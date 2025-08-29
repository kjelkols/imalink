# Globale definisjoner og konfigurasjoner for backend
# Plassering av databasefilen er endret til en fast plass utenfor prosjektmappen
# for å unngå problemer med sletting ved oppdatering av prosjektet.

DB_ROOT = "C:\\temp\\00imalink"  # Plass for lagrede data
DB_PATH = f"{DB_ROOT}\\mini.db"  # Full sti til databasefilen
LARGE_PATH = f"{DB_ROOT}\\large"  # Plass for lagring av store bilder

#DB_PATH = "C:\\temp\\00imalink\\mini.db" # Filen er nå plassert på en fast plass utenfor prosjektmappen
THUMBNAIL_SIZE = (80, 80) # Bør være en optimal størrelse for lagring og visning
LARGE_SIZE = (1600, 1600) # Størrelse for visning av bilder i fullskjerm
COMMON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
RAW_EXTENSIONS = {'cr2', 'nef', 'arw'}
ALLOWED_EXTENSIONS = COMMON_EXTENSIONS.union(RAW_EXTENSIONS)

if __name__ == "__main__":
    print(f"Konfigurasjon:\nDB_PATH: {DB_PATH}\nTHUMBNAIL_SIZE: {THUMBNAIL_SIZE}\nALLOWED_EXTENSIONS: {ALLOWED_EXTENSIONS}")