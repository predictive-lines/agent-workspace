const fs = require('fs');
const path = require('path');
const { google } = require('/home/open-claw/repos/google-workspace-mcp-live/node_modules/googleapis');

const docs = [
  ['1CKCss6S7ecGTZWSW37S5nsmttwsv4TrV', 'current-state-process-documentation-efp.kevin.docx', 'current-state-process-documentation-efp.verify-kevin.docx'],
  ['1DpEKHl-HFNT075bjtGwsS9BVV3gmGdnt', 'gap-analysis-efp.kevin.docx', 'gap-analysis-efp.verify-kevin.docx'],
  ['1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO', 'modernization-plan-efp.kevin.docx', 'modernization-plan-efp.verify-kevin.docx'],
];

async function auth() {
  const token = JSON.parse(fs.readFileSync('/home/open-claw/.google-mcp/tokens/predictivelines.json', 'utf8'));
  const oauth2 = new google.auth.OAuth2(token.client_id, token.client_secret, 'urn:ietf:wg:oauth:2.0:oob');
  oauth2.setCredentials({ refresh_token: token.refresh_token });
  return oauth2;
}

async function uploadAndVerify(drive, [fileId, localName, verifyName]) {
  const local = path.resolve('efp_modernization_work', localName);
  const before = await drive.files.get({ fileId, fields: 'id,name,modifiedTime,size,webViewLink' });
  console.log('before', before.data);
  const after = await drive.files.update({
    fileId,
    media: { mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', body: fs.createReadStream(local) },
    fields: 'id,name,modifiedTime,size,webViewLink',
  });
  console.log('after', after.data);
  const dest = path.resolve('efp_modernization_work', verifyName);
  const dl = await drive.files.get({ fileId, alt: 'media' }, { responseType: 'stream' });
  await new Promise((resolve, reject) => {
    const out = fs.createWriteStream(dest);
    dl.data.pipe(out);
    dl.data.on('error', reject);
    out.on('finish', resolve);
    out.on('error', reject);
  });
  console.log('verified download', dest, fs.statSync(dest).size);
}

async function main(){
  const drive = google.drive({version:'v3', auth: await auth()});
  for (const d of docs) await uploadAndVerify(drive, d);
}
main().catch(err=>{console.error(err.response?.data || err.stack || err.message || err); process.exit(1);});
