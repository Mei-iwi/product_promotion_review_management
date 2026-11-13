// New development replica stack only. Never drops or imports business data.
const uri = 'mongodb://' + encodeURIComponent(process.env.MONGO_ROOT_USERNAME) + ':' +
  encodeURIComponent(process.env.MONGO_ROOT_PASSWORD) + '@mongodb:27017/admin?directConnection=true';
let ready = false;
for (let attempt = 0; attempt < 90; attempt++) {
  try {
    const admin = new Mongo(uri).getDB('admin');
    let status;
    try { status = admin.runCommand({ replSetGetStatus: 1 }); }
    catch (error) { if (error.code !== 94) throw error; status = { code: 94 }; }
    if (status.code === 94) {
      assert.commandWorked(admin.runCommand({ replSetInitiate: { _id: 'rs0', members: [{ _id: 0, host: 'mongodb:27017' }] } }));
    } else if (!status.ok && status.code !== 94) {
      throw new Error('Replica set status unavailable');
    }
    if (admin.runCommand({ hello: 1 }).isWritablePrimary) { ready = true; break; }
  } catch (error) {
    // Startup / initial sync can temporarily reject connections. Never print URI.
  }
  sleep(1000);
}
if (!ready) { print('Replica initialization failed; check MongoDB service'); quit(1); }
print('Replica set rs0 is ready. Run reconcile-promotion-usage after importing data.');
