# Security policy

## Scope

Tiny Recorder is a local desktop tool. It has no server, no network code and no account, and it does not send your recordings anywhere. The sensitive items are:

- The recordings themselves (MP3 files in your output folder, `Documents\Tiny Recorder` by default). They can hold other people's voices: see "Responsible use" in the README.
- The local settings in `%APPDATA%\TinyRecorder`.

## Handling of secrets

- The app uses no API keys. Secrets and local settings are never part of this repository: `.gitignore` excludes configuration, settings, `.env`, key files and audio files.
- The repository contains no recordings.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Email **junqueira.ch@gmail.com** with the subject "Security: tiny-recorder" and include the version, what you observed and how to reproduce it. I aim to answer within 7 days.

## Supported versions

Only the latest release on the `main` branch is supported. Older versions in `archive/versions/` are kept for history and are not maintained.
