# SAP SR Tracker (desktop)

Tool desktop Windows per tracciare SR SAP per cliente (con link e descrizione) usando un database Postgres su Supabase.

## Funzioni
- CRUD SR: aggiungi / aggiorna / elimina
- Filtri: Cliente (tendina), Status, testo, "Aperta da" (case-insensitive)
- Export CSV della vista filtrata
- Doppio click sul link per aprire la SR nel browser
- Check aggiornamenti: apre la pagina GitHub Releases se c’è una versione più nuova

## Prerequisiti (utente)
- Windows 10/11
- Accesso internet verso Supabase (porta 5432 verso `*.pooler.supabase.com`)

## Prima configurazione (1 minuto)
Il tool legge la configurazione DB da variabili d’ambiente Windows (così la password non è dentro l’eseguibile) (da chiedere a Pasquale).

Apri **cmd** e incolla:

```bat
setx SRDB_USER "postgres.<PROJECT_REF>"
setx SRDB_PASS "LA_TUA_PASSWORD"
setx SRDB_HOST "aws-1-eu-west-1.pooler.supabase.com"
setx SRDB_PORT "5432"
setx SRDB_NAME "postgres"
