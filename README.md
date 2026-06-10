# VINScan — Full Stack App (v2)

Full-stack used car history app. Scan a VIN → get accidents, ownership,
recalls, title flags, market value, and a Buy Confidence Score (0–100).

## What's included (v2 — full US playbook)

### Consumer features
- VIN barcode scan + manual entry
- Full vehicle history report (NHTSA + VINAudit)
- Buy Confidence Score (0–100)
- Accident detail: severity, airbags, damage areas
- Ownership chain with dates and states
- Odometer timeline with rollback detection
- Title flags: salvage, flood, lemon, frame damage, theft
- NHTSA safety recalls (live, always current)
- Market value estimate
- Affiliate cards: insurance, financing, warranty, inspection
- PDF report export (consumer + white-label)

### Retention features
- My Garage: track owned vehicles, monitor recalls
- Recall push notifications (nightly NHTSA check via Celery Beat)
- In-app review prompt (triggered after 3rd clean report)
- Lookup history

### Dealer / B2B features
- Dealer plan ($300/mo) via Stripe
- Batch VIN lookup (up to 50 VINs per request)
- White-label PDF reports with dealer branding
- Dealer usage dashboard
- B2B API key authentication (X-API-Key header)
- API key management (create / revoke)

### Payments
- $5 single lookup (one-time Stripe payment)
- $10/month consumer subscription
- $300/month dealer subscription
- Stripe webhook handler (checkout, renewal, cancellation, failed payment)

## Project structure

```
vin-app/
  README.md
  .gitignore
  backend/                          Django API
    manage.py
    requirements.txt
    Procfile
    railway.json
    .env.example
    .github/workflows/deploy.yml
    vin_project/
      settings.py                   All config including Celery Beat schedule
      urls.py                       All 20+ routes
      celery.py
      wsgi.py
    reports/
      models.py                     VehicleReport, ReportLookup, OwnedVehicle
      views.py                      Report, PDF, batch, dealer, garage endpoints
      validators.py                 VIN 17-char + checksum validation
      tasks.py                      fetch_vehicle_report, check_new_recalls_and_notify
      services/
        nhtsa.py                    Free NHTSA decode + recall API
        vinaudit.py                 VINAudit history API
        scoring.py                  Severity-weighted risk score
        pdf_generator.py            WeasyPrint PDF export
      templates/reports/
        report_pdf.html             Branded PDF template
    users/
      models.py                     User, DealerProfile, PushToken, APIKey
      authentication.py             API key auth backend
      services/
        stripe_service.py           Consumer + dealer Stripe checkout
      views/
        payments.py                 Checkout, billing, cancel endpoints
        webhooks.py                 Stripe event handler
        push.py                     Push token registration
        api_keys.py                 API key CRUD
  frontend/                         React Native (Expo)
    App.tsx                         Entry + OTA updates + push registration
    app.json
    eas.json
    package.json
    src/
      navigation/AppNavigator.tsx   Tabs: Scan, History, Garage, Profile
      services/
        api.ts                      All 20+ Django API calls
        notifications.ts            Expo push token registration
        review.ts                   In-app review prompt logic
      components/
        AffiliateCards.tsx          Insurance / financing / warranty cards
      screens/
        LoginScreen.tsx
        ScannerScreen.tsx           Expo camera + barcode + manual entry
        ReportScreen.tsx            Full report with all data sections
        HistoryScreen.tsx           Past lookups
        GarageScreen.tsx            Owned vehicle tracker
        ProfileScreen.tsx           Billing status + cancel
        PaywallScreen.tsx           $5 vs $10/mo choice
```

## Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # fill in your keys
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver   # terminal 1
celery -A vin_project worker --loglevel=info          # terminal 2
celery -A vin_project beat   --loglevel=info          # terminal 3 (recall notifications)
redis-server                                           # terminal 4
```

## Frontend setup

```bash
cd frontend
npm install
# Update BASE_URL in src/services/api.ts to your Railway URL
npx expo start
```

## Deploy to Railway

```bash
npm install -g @railway/cli
railway login && railway init
# Add PostgreSQL + Redis from Railway dashboard
railway variables set SECRET_KEY="..." STRIPE_SECRET_KEY="..." # etc.
railway up
railway run python manage.py migrate
```

## Build + submit mobile apps

```bash
npm install -g eas-cli && eas login
eas build --platform all --profile production
eas submit --platform all
# JS-only updates (no store review):
eas update --branch production --message "Fix"
```

## Stripe setup

Create 3 products in the Stripe dashboard:
- Monthly plan: Recurring · $10/month → STRIPE_MONTHLY_PRICE_ID
- Single lookup: One-time · $5       → STRIPE_LOOKUP_PRICE_ID
- Dealer plan:  Recurring · $300/month → STRIPE_DEALER_PRICE_ID

Register webhook: https://your-app.railway.app/api/webhooks/stripe/
Events: checkout.session.completed, customer.subscription.updated,
        customer.subscription.deleted, invoice.payment_failed

Test locally: stripe listen --forward-to localhost:8000/api/webhooks/stripe/
Test card: 4242 4242 4242 4242

## B2B API usage

Enterprise clients authenticate with an API key instead of JWT:

  curl -X POST https://your-app.railway.app/api/report/ \
    -H "X-API-Key: their-key" \
    -H "Content-Type: application/json" \
    -d '{"vin": "1HGBH41JXMN109186"}'

Keys are created and managed at /api/keys/.

## Revenue model

| Channel                  | Unit price | Target         | Annual revenue |
|--------------------------|------------|----------------|----------------|
| Consumer subscriptions   | $10/mo     | 3,000 users    | $360,000       |
| Single lookups           | $5 each    | 80,000/yr      | $400,000       |
| Dealer plans             | $300/mo    | 20 dealers     | $72,000        |
| Affiliate commissions    | Varies     | Insurance etc. | $80,000        |
| White-label / API deals  | $50K+      | 2 partners     | $100,000       |
| Total Year 2–3 target    |            |                | $1,012,000     |
