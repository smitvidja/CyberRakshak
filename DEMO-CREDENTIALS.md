# Demo credentials

All identities below are synthetic/local-only mock eKYC records - no real Aadhaar, UIDAI, or
mobile carrier is ever contacted. Verify at `/en/cyber-warrior/verify` (Cyber Warrior) or from the
citizen entry flow on the home page (identified complaint path). Each identity works with either
role, but the two groups below are kept separate by *usage history*, not by any code restriction.

## Already used (existing application/reports on file)

Use these to see the **returning-user** experience (verifying takes you straight to the
dashboard, not through registration again):

- Rahul Kumar: `99000000000001` / OTP `123456`
- Ananya Shah: `99000000000002` / OTP `654321`

## Reserved for a full first-time Cyber Warrior journey

Never used - each of these will take a reviewer through profile setup -> resume upload/parsing ->
application review & submit from scratch. Use a different one each time you want to demo the
journey again (an identity that has already submitted a Cyber Warrior application will redirect
straight to its dashboard on the next verification, per the returning-user routing).

| Name | Identity ID | OTP | City |
|---|---|---|---|
| Rohan Mehta | `99000000000003` | `111222` | Pune, Maharashtra |
| Priya Nair | `99000000000004` | `222333` | Kochi, Kerala |
| Karan Verma | `99000000000005` | `333444` | Jaipur, Rajasthan |
| Sneha Iyer | `99000000000006` | `444555` | Chennai, Tamil Nadu |
| Arjun Malhotra | `99000000000007` | `555666` | Chandigarh |

Resume upload works the same for any identity - the resume parser is a **static mock** (it always
returns the same synthetic sample data: skills, one education entry, one experience entry, one
certification) regardless of the file's real content. There's no real text-extraction/AI parsing
in this MVP; the review step exists to demonstrate the "confirm what was extracted before it's
saved to your profile" flow, not real resume analysis.

## Reserved for a full first-time citizen/victim journey

Never used - for demoing identified complaint registration, profile auto-fill, and "My Reports"
from a clean slate:

| Name | Identity ID | OTP | City |
|---|---|---|---|
| Neha Kapoor | `99000000000008` | `666777` | Lucknow, Uttar Pradesh |
| Vikram Choudhary | `99000000000009` | `777888` | Indore, Madhya Pradesh |
| Meera Joshi | `99000000000010` | `888999` | Bhopal, Madhya Pradesh |
| Aditya Rao | `99000000000011` | `999000` | Bengaluru, Karnataka |

## Notes

- Each demo OTP is single-use per verification - request a fresh OTP (via the "Resend OTP"
  button) before verifying again with the same identity.
- All 11 identities are defined in `backend/app/services/mock_identity_service.py`
  (`DEMO_IDENTITIES`) and are auto-seeded into the database on first use - no migration or manual
  DB setup is needed to use any of them.
- `backend/scripts/reset_demo_warrior_data.py` clears Cyber Warrior demo data (profile,
  application, resume results, reports) so you can redo the full first-time journey with the
  same identity again. No special app permission ("admin role", etc.) is needed - it's a plain
  local script, run from the `backend/` directory with the project virtualenv:
  ```
  python scripts/reset_demo_warrior_data.py                          # resets every identity above
  python scripts/reset_demo_warrior_data.py 99000000000003           # resets just Rohan Mehta
  python scripts/reset_demo_warrior_data.py 99000000000001 99000000000002   # resets Rahul + Ananya
  ```
  It never touches citizen profiles/complaints, and never touches an identity's separate citizen
  account (only its Cyber Warrior side). The app's own `ADMIN` user role is unrelated to this -
  that role is only for reviewing complaints/suspect reports/warrior applications inside the
  product itself, not for resetting demo data.
