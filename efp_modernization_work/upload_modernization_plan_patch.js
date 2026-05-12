const fs = require('fs');
const path = require('path');
const { google } = require('/home/open-claw/repos/google-workspace-mcp-live/node_modules/googleapis');

const FILE_ID = '1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO';
const LOCAL = path.resolve('efp_modernization_work/modernization-plan-efp.daily-reporting.docx');

async function auth() {
  const token = JSON.parse(fs.readFileSync('/home/open-claw/.google-mcp/tokens/predictivelines.json', 'utf8'));
  const oauth2 = new google.auth.OAuth2(token.client_id, token.client_secret, 'urn:ietf:wg:oauth:2.0:oob');
  oauth2.setCredentials({ refresh_token: token.refresh_token });
  return oauth2;
}

async function main() {
  const drive = google.drive({ version: 'v3', auth: await auth() });
  const before = await drive.files.get({ fileId: FILE_ID, fields: 'id,name,mimeType,modifiedTime,size,webViewLink' });
  console.log('before', before.data);
  const res = await drive.files.update({
    fileId: FILE_ID,
    media: {
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      body: fs.createReadStream(LOCAL),
    },
    fields: 'id,name,mimeType,modifiedTime,size,webViewLink',
  });
  console.log('after', res.data);
  const dest = path.resolve('efp_modernization_work/modernization-plan-efp.daily-reporting.verify.docx');
  const dl = await drive.files.get({ fileId: FILE_ID, alt: 'media' }, { responseType: 'stream' });
  await new Promise((resolve, reject) => {
    const out = fs.createWriteStream(dest);
    dl.data.pipe(out);
    dl.data.on('error', reject);
    out.on('finish', resolve);
    out.on('error', reject);
  });
  console.log('downloaded', dest, fs.statSync(dest).size);
}

main().catch(err => {
  console.error(err.response?.data || err.stack || err.message || err);
  process.exit(1);
});
