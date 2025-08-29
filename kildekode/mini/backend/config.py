# Globale definisjoner og konfigurasjoner for backend
# Plassering av databasefilen er endret til en fast plass utenfor prosjektmappen
# for å unngå problemer med sletting ved oppdatering av prosjektet.

DB_PATH = "C:\\temp\\00imalink\\mini.db" # Filen er nå plassert på en fast plass utenfor prosjektmappen
THUMBNAIL_SIZE = (80, 80) # Bør være en optimal størrelse for lagring og visning
COMMON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
RAW_EXTENSIONS = {'cr2', 'nef', 'arw'}
ALLOWED_EXTENSIONS = COMMON_EXTENSIONS.union(RAW_EXTENSIONS)

