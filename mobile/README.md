# 📱 Mobile App (Capacitor.js Native Wrapper)

This directory provides the mobile configuration to wrap the Universal Video Downloader into a native Android app (`.apk` and `.aab` for Google Play Store).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Node.js 18+ & npm installed.
- Android Studio installed with Android SDK 34 (Android 14).

### 2. Install Capacitor CLI & Dependencies
In this `mobile` folder:
```bash
npm install
```

### 3. Initialize Android Platform
Add the Android native project:
```bash
npx cap add android
```
*(This automatically creates the native Android Studio project linked to `../backend/static`)*.

### 4. Open in Android Studio
```bash
npx cap open android
```
- From Android Studio, you can run directly on an Android emulator or a physical phone via USB.
- To generate the release APK / Bundle:
  `Build -> Generate Signed Bundle / APK...`

---

## ⚠️ Google Play Store Submission Guidelines

### Crucial Policy Requirement:
Google Play strictly prohibits apps that download YouTube content under Section 4.4 of the Developer Distribution Agreement:
> *"You agree not to access, or attempt to access, YouTube videos for download."*

### Compliant Dual-Release Strategy:
1. **Google Play Store Release**:
   - Set the client store identifier: `target_store = "playstore"`
   - YouTube links will display an alert: *"YouTube downloading is disabled for Google Play compliance. Use our Web app for YouTube downloads."*
   - Supported on Play Store: **TikTok (including Drama series), Instagram Reels, Facebook Videos, X / Twitter, Reddit, and Pinterest.**
2. **Direct APK / Web Release (Full Features)**:
   - Provide direct `.apk` downloads from your website or platforms like APKPure / Uptodown with **YouTube 4K & MP3 enabled**.

---

## 📁 Android MediaStore & Gallery Saving
When files are saved on Android, Capacitor's `@capacitor/filesystem` writes to:
- `Directory.Documents` or `Directory.ExternalStorage`
- Video files are scanned into Android's `MediaStore` so they immediately appear in the user's **Gallery / Google Photos** app.
