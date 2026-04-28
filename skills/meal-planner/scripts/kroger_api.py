#!/usr/bin/env python3
"""Kroger API client for the meal-planner skill.

Handles:
- Client credentials auth (product search, location lookup)
- User OAuth2 auth (cart operations) with token persistence
- Product search by term + location
- Cart add (requires user OAuth token)
- Location search

Credentials: ~/.config/kroger/credentials.json
Tokens: ~/.config/kroger/tokens.json
"""

import json
import os
import sys
import time
import base64
import urllib.parse
from pathlib import Path

import requests

CREDS_PATH = Path.home() / ".config" / "kroger" / "credentials.json"
TOKENS_PATH = Path.home() / ".config" / "kroger" / "tokens.json"
API_BASE = "https://api.kroger.com/v1"
BRIGHTON_LOCATION_ID = "01800638"
DEFAULT_REDIRECT_URI = "https://oauthdebugger.com/debug"


def load_creds():
    with open(CREDS_PATH) as f:
        return json.load(f)


def get_client_token(creds=None):
    """Get a client credentials token (for product search, locations)."""
    if creds is None:
        creds = load_creds()
    resp = requests.post(
        f"{API_BASE}/connect/oauth2/token",
        auth=(creds["client_id"], creds["client_secret"]),
        data={"grant_type": "client_credentials", "scope": "product.compact"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def save_user_tokens(token_data):
    """Persist user OAuth tokens."""
    token_data["saved_at"] = time.time()
    with open(TOKENS_PATH, "w") as f:
        json.dump(token_data, f, indent=2)


def load_user_tokens():
    """Load persisted user tokens, return None if not found."""
    if not TOKENS_PATH.exists():
        return None
    with open(TOKENS_PATH) as f:
        return json.load(f)


def refresh_user_token(creds=None):
    """Refresh user token using refresh_token grant."""
    if creds is None:
        creds = load_creds()
    tokens = load_user_tokens()
    if not tokens or "refresh_token" not in tokens:
        return None
    resp = requests.post(
        f"{API_BASE}/connect/oauth2/token",
        auth=(creds["client_id"], creds["client_secret"]),
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
    )
    if resp.status_code != 200:
        return None
    token_data = resp.json()
    # Preserve refresh_token if not returned in refresh response
    if "refresh_token" not in token_data and "refresh_token" in tokens:
        token_data["refresh_token"] = tokens["refresh_token"]
    save_user_tokens(token_data)
    return token_data["access_token"]


def get_user_token(creds=None):
    """Get a valid user access token. Refreshes if expired."""
    tokens = load_user_tokens()
    if tokens:
        # Check if expired (with 60s buffer)
        saved_at = tokens.get("saved_at", 0)
        expires_in = tokens.get("expires_in", 1800)
        if time.time() < saved_at + expires_in - 60:
            return tokens["access_token"]
        # Try refresh
        refreshed = refresh_user_token(creds)
        if refreshed:
            return refreshed
    return None


def get_auth_url(creds=None, redirect_uri=DEFAULT_REDIRECT_URI):
    """Generate the OAuth2 authorization URL for user login."""
    if creds is None:
        creds = load_creds()
    params = {
        "scope": "cart.basic:write profile.compact",
        "response_type": "code",
        "client_id": creds["client_id"],
        "redirect_uri": redirect_uri,
    }
    return f"{API_BASE}/connect/oauth2/authorize?{urllib.parse.urlencode(params)}"


def exchange_code(code, redirect_uri=DEFAULT_REDIRECT_URI, creds=None):
    """Exchange authorization code for user tokens."""
    if creds is None:
        creds = load_creds()
    resp = requests.post(
        f"{API_BASE}/connect/oauth2/token",
        auth=(creds["client_id"], creds["client_secret"]),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    resp.raise_for_status()
    token_data = resp.json()
    save_user_tokens(token_data)
    return token_data["access_token"]


def search_locations(zip_code="48116", radius=10, limit=5, token=None):
    """Search for Kroger locations near a zip code."""
    if token is None:
        token = get_client_token()
    resp = requests.get(
        f"{API_BASE}/locations",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "filter.zipCode.near": zip_code,
            "filter.radiusInMiles": radius,
            "filter.limit": limit,
        },
    )
    resp.raise_for_status()
    return resp.json()["data"]


def search_products(term, location_id=BRIGHTON_LOCATION_ID, limit=5, token=None):
    """Search for products at a specific Kroger location."""
    if token is None:
        token = get_client_token()
    resp = requests.get(
        f"{API_BASE}/products",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "filter.term": term,
            "filter.locationId": location_id,
            "filter.limit": limit,
        },
    )
    resp.raise_for_status()
    return resp.json()["data"]


def add_to_cart(items, user_token=None):
    """Add items to the user's Kroger cart.
    
    items: list of {"upc": "...", "quantity": N}
    Requires user OAuth token with cart.basic:write scope.
    """
    if user_token is None:
        user_token = get_user_token()
    if not user_token:
        raise RuntimeError(
            "No user token available. Run OAuth flow first: "
            "python3 kroger_api.py auth"
        )
    resp = requests.put(
        f"{API_BASE}/cart/add",
        headers={
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={"items": items},
    )
    if resp.status_code == 401:
        # Try refresh
        refreshed = refresh_user_token()
        if refreshed:
            resp = requests.put(
                f"{API_BASE}/cart/add",
                headers={
                    "Authorization": f"Bearer {refreshed}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"items": items},
            )
    resp.raise_for_status()
    return resp.status_code == 204 or resp.status_code == 200


def start_auth_flow():
    """Start the OAuth2 authorization flow using Kroger's registered redirect URI."""
    auth_url = get_auth_url(redirect_uri=DEFAULT_REDIRECT_URI)

    print(f"\n🔑 Open this URL in your browser to authorize:\n\n{auth_url}\n")
    print("After Kroger redirects to oauthdebugger.com, copy the `code` value from the URL and paste it here:")
    code = input("Authorization code: ").strip()

    if code:
        token = exchange_code(code, DEFAULT_REDIRECT_URI)
        print(f"✅ Authorized! Token saved to {TOKENS_PATH}")
        return token
    else:
        print("❌ No authorization code received.")
        return None


# --- CLI ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: kroger_api.py <command> [args]")
        print("Commands: auth, search <term>, locations <zip>, cart-add <upc> <qty>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "auth":
        start_auth_flow()
    
    elif cmd == "search":
        term = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "milk"
        results = search_products(term)
        for p in results:
            items = p.get("items", [{}])
            price = items[0].get("price", {}) if items else {}
            size = items[0].get("size", "") if items else ""
            print(f"UPC: {p['upc']} | {p['description']} | {size} | ${price.get('regular', 'N/A')}")
    
    elif cmd == "locations":
        zip_code = sys.argv[2] if len(sys.argv) > 2 else "48116"
        locs = search_locations(zip_code)
        for loc in locs:
            addr = loc.get("address", {})
            print(f"ID: {loc['locationId']} | {loc.get('name', '')} | {addr.get('addressLine1', '')} {addr.get('city', '')} {addr.get('state', '')}")
    
    elif cmd == "cart-add":
        if len(sys.argv) < 4:
            print("Usage: kroger_api.py cart-add <upc> <quantity>")
            sys.exit(1)
        upc = sys.argv[2]
        qty = int(sys.argv[3])
        result = add_to_cart([{"upc": upc, "quantity": qty}])
        print(f"✅ Added {qty}x {upc} to cart" if result else "❌ Failed")
    
    elif cmd == "token-status":
        tokens = load_user_tokens()
        if tokens:
            saved = tokens.get("saved_at", 0)
            expires = tokens.get("expires_in", 1800)
            remaining = (saved + expires) - time.time()
            print(f"User token: {'valid' if remaining > 0 else 'expired'} ({int(remaining)}s remaining)")
            print(f"Refresh token: {'present' if 'refresh_token' in tokens else 'missing'}")
        else:
            print("No user tokens found. Run: kroger_api.py auth")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
