# Flask to Django Confirmation Views Mapping

## Password Reset
**Flask views:** `reset_password_get()`, `reset_password_post()`, `reset_password_institution_get()`, `reset_password_institution_post()`, `forgot_password_get()`, `forgot_password_post()`, `forgot_password_institution_post()`

**Django equivalent:** `ResetPassword` (handles both GET and POST)
- **File:** [api/users/views.py](api/users/views.py#L812)
- **Route:** `/v2/users/reset_password/`
- **Status:** Partial implementation - needs update for institutional variant
- **Verified:** Password reset

---

## First time external login
**Flask view:** `external_login_email_get()`, `external_login_email_post()`

**Django equivalent:** `ExternalLogin`
- **File:** [api/users/views.py](api/users/views.py#L715)
- **Route:** `/v2/users/external_login/`
- **Status:** Implemented (handles first-time OAuth user email submission)
- **Notes:** Creates unconfirmed user or links existing user with external identity

---

## External Login Email Confirmation
**Flask view:** `external_login_confirm_email_get()`

**Django equivalent:** `ExternalLoginConfirmEmailView`
- **File:** [api/users/views.py](api/users/views.py#L1429)
- **Route:** `/v2/users/external_login_confirm_email/`
- **HTTP Method:** POST
- **Status:** Implemented (Django POST version of Flask GET)
- **Notes:** Verifies email confirmation link for first-time OAuth login (CREATE or LINK status)

---

## Email Confirmation (General)
**Flask view:** `confirm_email_get()`

**Django equivalent:** `ConfirmEmailView`
- **File:** [api/users/views.py](api/users/views.py#L1132)
- **Route:** `/v2/users/<user_id>/confirm/`
- **HTTP Method:** POST
- **Status:** Implemented
- **Notes:** Handles email confirmation for initial account creation, email addition, and external identity linking
- **Verified:** email confirmation for initial account creation

---

## Add/Merge Email Confirmation (At Login)
**Flask views:** `unconfirmed_email_add()`, `unconfirmed_email_remove()`

**Django equivalent:** `UserEmailsList` (POST to add), `UserEmailsDetail` (DELETE to remove)
- **File:** [api/users/views.py](api/users/views.py#L1281) and [api/users/views.py](api/users/views.py#L1326)
- **Routes:**
  - `/v2/users/<user_id>/emails/` (POST to add email)
  - `/v2/users/<user_id>/emails/<email_id>/` (DELETE to remove unconfirmed email)
- **Status:** Partially implemented (needs verification of merge behavior)
- **Notes:** Handles user email additions and removals at login; merge logic needs verification
- **Verified:** additions and removals already used by ANG

---

## Contributor Claim
**Flask views:** Claims handled implicitly through `confirm_email_get()` with merge context

**Django equivalents:**
1. **Initiate claim:** `ClaimUser`
   - **File:** [api/users/views.py](api/users/views.py#L967)
   - **Route:** `/v2/users/<user_id>/claim/`
   - **HTTP Method:** POST
   - **Status:** Implemented
   - **Notes:** Sends claim email to unregistered contributor

2. **Confirm claim (set password):** `ConfirmClaimUser`
   - **File:** [api/users/views.py](api/users/views.py#L1051)
   - **Route:** `/v2/users/<user_id>/confirm_claim/`
   - **HTTP Method:** POST
   - **Status:** Implemented
   - **Notes:** Sets password for claimed user, clears unclaimed records

---

## Resend Confirmation Email
**Flask views:** `resend_confirmation_get()`, `resend_confirmation_post()`

**Django equivalent:** `UserEmailsDetail` (with `resend_confirmation` query param)
- **File:** [api/users/views.py](api/users/views.py#L1326)
- **Route:** `/v2/users/<user_id>/emails/<email_id>/?resend_confirmation=true`
- **HTTP Method:** GET (with query parameter)
- **Status:** Implemented (via query parameter on email detail endpoint)
- **Notes:** Resends confirmation email if throttle period has expired
- **Verified:** already used by ANG



## Key Differences

1. **HTTP Methods**: Flask uses GET for landing pages and POST for form submission. Django consolidates these into single views using GET/POST.

2. **Institutional Variants**: Flask has separate institutional views; Django uses query parameter for institutional flag (needs verification/update).


# Flask Confirmation Views WITHOUT Django Equivalents

## Authentication & Registration Views (No Django Equivalent Yet)

### 1. User Registration Page
**Flask view:** `auth_register(auth)`
- **File:** [framework/auth/views.py](framework/auth/views.py#L426)
- **Flask Route:** `GET /register/`
- **Renderer:** `public/register.mako`
- **Purpose:** Renders user registration form page
- **Status:** ❌ No Django equivalent
- **Notes:** Returns registration form context for rendering registration page

---

### 2. User Login Page
**Flask view:** `auth_login(auth)`
- **File:** [framework/auth/views.py](framework/auth/views.py#L400)
- **Flask Routes:**
  - `GET /login/`
  - `GET /account/`
- **Purpose:** Renders login form page (handles OSF login and campaign login)
- **Status:** ❌ No Django equivalent
- **Notes:** Routes users to appropriate login page; supports campaign-specific login flows

---

### 3. User Logout
**Flask view:** `auth_logout(auth, redirect_url=None, next_url=None)`
- **File:** [framework/auth/views.py](framework/auth/views.py#L487)
- **Flask Route:** `GET /logout/`
- **Purpose:** Logs out user from OSF and CAS, manages cookie deletion
- **Status:** ❌ No Django equivalent
- **Notes:** Handles complex logout flow: OSF logout → CAS logout, manages redirect URLs and `reauth` parameter

---

### 4. API User Registration Endpoint
**Flask view:** `register_user(**kwargs)`
- **File:** [framework/auth/views.py](framework/auth/views.py#L877)
- **Flask Route:** `POST /api/v1/register/`
- **Renderer:** `json_renderer`
- **Purpose:** API endpoint for registering new user account
- **Status:** ❌ No Django equivalent
- **Notes:** Handles form validation, user creation, confirmation email sending. Returns JSON response

---

## Email-Related Views (No Django Equivalent Yet)

### 5. Email Logout (Merge/Add Email)
**Flask view:** `auth_email_logout(token, user)`
- **File:** [framework/auth/views.py](framework/auth/views.py#L543)
- **Purpose:** Internal handler for logout when user is adding email or merging accounts
- **Status:** ❌ No Django equivalent
- **Called by:** `confirm_email_get()` (line 701)
- **Notes:**
  - Confirms email via token
  - Checks for merge target (existing user with same email)
  - Logs out both users if merge is happening
  - Deletes OSF cookie
  - Redirects to CAS logout → CAS login with service URL

---

## Institution-Specific Views (No Django Equivalent Yet)

### 6. Redirect Unsupported Institution
**Flask view:** `redirect_unsupported_institution(auth)`
- **File:** [framework/auth/views.py](framework/auth/views.py#L185)
- **Flask Route:** `GET /forgotpassword-institution/`
- **Purpose:** Redirects to unsupported institution page on CAS
- **Status:** ❌ No Django equivalent
- **Notes:** Used when user tries institutional password reset but institution is not supported; logs out user if logged in first
