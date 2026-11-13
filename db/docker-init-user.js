// Mongo's entrypoint runs this ONLY for an empty data directory. Business
// collections are never seeded or dropped. Existing volumes need an operator
// to provision credentials before enabling --auth; see docs/SECURITY.md.
const applicationDatabase = process.env.MONGO_DB;
const applicationUser = process.env.MONGO_APP_USERNAME;
const applicationPassword = process.env.MONGO_APP_PASSWORD;
if (!applicationDatabase || !applicationUser || !applicationPassword) {
  throw new Error('Missing MongoDB application credentials');
}
db.getSiblingDB(applicationDatabase).createUser({
  user: applicationUser,
  pwd: applicationPassword,
  roles: [{ role: 'readWrite', db: applicationDatabase }],
});
