# SAP SR Tracker (Windows Desktop)

Tool desktop per Windows per tracciare SR SAP per cliente (con link e descrizione) usando un database Postgres su Supabase.

## Download (per tester)

### Opzione 1 (consigliata): scarica l’ultima versione (sempre)
- EXE (download diretto):
  https://github.com/Pasqualeim/sr_tracker/releases/latest/download/SAP-SR-Tracker.exe

- Pagina “Latest release” (note, changelog, altri file):
  https://github.com/Pasqualeim/sr_tracker/releases/latest

> Se il link diretto non funziona, apri la pagina “Latest release” e scarica l’asset manualmente.

### Opzione 2: link a una versione specifica
- Release v0.3.4:
  https://github.com/Pasqualeim/sr_tracker/releases/tag/v0.3.4


## Funzioni principali

- CRUD SR: aggiungi / aggiorna / elimina
- Filtri: Cliente (tendina), Status, testo (SR o descrizione), “Aperta da” (case-insensitive)
- Export CSV della vista filtrata
- Doppio click sul link per aprire la SR nel browser
- Aggiornamenti: controlla automaticamente se esiste una versione più nuova e propone l’apertura della pagina Releases


## Prerequisiti (utente)

- Windows 10 / Windows 11
- Accesso internet verso Supabase:
  - Porta: 5432
  - Host: `*.pooler.supabase.com`
- Permessi: l’utente deve poter eseguire file `.exe` scaricati (in alcune aziende Windows può bloccarli)


## Prima configurazione (1 minuto)

L’app legge la configurazione DB da variabili d’ambiente Windows (così la password non è dentro l’eseguibile).

### 1) Recupera i parametri DB
Chiedili a Pasquale (SRDB_USER / SRDB_PASS / SRDB_HOST / SRDB_PORT / SRDB_NAME).

### 2) Imposta le variabili (CMD)
Apri **Prompt dei comandi (cmd)** e incolla (sostituisci i valori):

```bat
setx SRDB_USER "postgres.<PROJECT_REF>"
setx SRDB_PASS "LA_TUA_PASSWORD"
setx SRDB_HOST "aws-1-eu-west-1.pooler.supabase.com"
setx SRDB_PORT "5432"
setx SRDB_NAME "postgres"
