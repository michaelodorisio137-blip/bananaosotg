# AzeezOS 2.0 development preview

Based on the 0.5.3.9 GBA bitmap fix OTA. Only the new UI binary and its sort default/version are overlaid onto that root filesystem; existing cores are preserved. Do not publish this to the production OTA feed.

Implemented in dev.1: region sort, touch-accessible AI Cheats research panel for the existing single-screen RetroArch/BananaFront game panel, separate prompt keyboard, source-backed online lookup through OpenAI Responses API, save unverified research drafts, and confirmed game reset via RESET. The API key must be provided in the banana-ui service environment (AZEEZOS_OPENAI_API_KEY or OPENAI_API_KEY); no credentials are included or stored by this module. The model defaults to gpt-5-mini and is configurable with AZEEZOS_AI_MODEL. Only game metadata, file CRC32/size and prompt are sent. No ROM upload. API billing is separate.

Not implemented in dev.1: AI memory search, candidate application, user-confirmed working cheat catalog, cheat toggles, dual-screen DS overlay, Mods browser, AI self-upgrading agent, permanent six-tab dashboard. Do not describe this preview as a complete 2.0. No AI output is executed. The source-backed draft is not a verified cheat. Reset resets the current core and does not replace the ROM. Requires hardware validation.

Next: authenticated build service, per-emulator cheat adapters, exact ROM SHA-256 identity, temporary test and restore, live memory differential search, confirmation, persistent enabled cheats, DS overlay, mod downloads/patch verification, signed build manifests and recovery.
