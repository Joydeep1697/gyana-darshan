# Free Render demo deployment

Nyaya Darshan can run on Render's free web-service tier by using the repository
`render.yaml` blueprint.

The free blueprint intentionally does not attach a persistent disk because Render
free web services cannot preserve local filesystem changes with disks. Runtime
state uses `/tmp/nyaya`, which is suitable for a public demo, QA smoke tests, and
short-lived validation.

Do not treat the free Render deployment as durable production storage. Uploaded
documents, SQLite data, generated logs, and local operational records may be lost
after restart, redeploy, suspension, or infrastructure recycling.

For durable production, use one of these instead:

- a paid Render web service with persistent disk restored in `render.yaml`
- a managed database plus durable object/file storage
- another host that provides persistent volumes without requiring a paid upgrade

Required production/demo secrets still apply:

- `NVIDIA_API_KEY`
- `ALLOWED_ORIGINS=https://nyaya-darshan.onrender.com`
- `NYAYA_CREDENTIAL_ROTATION_CONFIRMED=true` after credential rotation
- Google OAuth variables only when Google login is enabled for the deployed URL
- Razorpay variables only when payment flows are enabled

The deployment remains labeled as an operational demo until credential rotation,
external legal validation, email delivery, OAuth callback QA, and durable storage
are completed.
