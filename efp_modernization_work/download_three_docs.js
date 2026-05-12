const fs = require('fs');
const path = require('path');
const { google } = require('/home/open-claw/repos/google-workspace-mcp-live/node_modules/googleapis');

const docs = [
  ['1CKCss6S7ecGTZWSW37S5nsmttwsv4TrV', 'current-state-process-documentation-efp.latest.docx'],
  ['1DpEKHl-HFNT075bjtGwsS9BVV3gmGdnt', 'gap-analysis-efp.latest.docx'],
  ['1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO', 'modernization-plan-efp.latest2.docx'],
];

async function auth() {
  const token = JSON.parse(fs.readFileSync('/home/open-claw/.google-mcp/tokens/predictivelines.json', 'utf8'));
  const oauth2 = new google.auth.OAuth2(token.client_id, token.client_secret, 'urn:ietf:wg:oauth:2.0:oob');
  oauth2.setCredentials({ refresh_token: token.refresh_token });
  return oauth2;
}

async function download(drive, fileId, filename) {
  const meta = await drive.files.get({ fileId, fields: 'id,name,mimeType,modifiedTime,size,webViewLink' });
  console.log('meta', meta.data);
  const dest = path.resolve('efp_modernization_work', filename);
  const res = await drive.files.get({ fileId, alt: 'media' }, { responseType: 'stream' });
  await new Promise((resolve, reject) => {
    const out = fs.createWriteStream(dest);
    res.data.pipe(out);
    res.data.on('error', reject);
    out.on('finish', resolve);
    out.on('error', reject);
  });
  console.log('downloaded', dest, fs.statSync(dest).size);
}

async function main() {
  const drive = google.drive({ version: 'v3', auth: await auth() });
  for (const d of docs) await download(drive, d[0], d[1]);
}

main().catch(err => { console.error(err.response?.data || err.stack || err.message || err); process.exit(1); });
