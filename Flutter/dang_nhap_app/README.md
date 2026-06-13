# Dang Nhap App Mobile

Android mobile Flutter version converted from the original `Fontend` HTML/CSS/JS screens.

## Run

```powershell
cd Flutter\dang_nhap_app
flutter pub get
flutter run
```

## Notes

- The UI is mobile-first for Android, with no web two-column layouts.
- Backend calls use the same Flask endpoints as the old frontend.
- Android emulator calls the host backend through `http://10.0.2.2:5000` in `lib/src/core/api_service.dart`.
- AI chat uses `http://10.0.2.2:5002`.
- If you run on a real phone, change `ApiConfig.baseUrl` to your computer's LAN IP.

## Converted Screens

- Auth: login, register, OTP verification, forgot/reset password.
- Main app: home, exercises, active plan, profile, FAQ/about/contact.
- Premium: SePay payment creation, QR display, payment status check.
- Admin: mobile card-based management for exercises, users, and content overview.
- Chat: mobile AI coach sheet using the same chat API.
