# Kravspesifikasjon: ImaLink Digitalt Bildehåndteringssystem

## 1. Innledning
### 1.1 Formål
ImaLink skal tilby en løsning for organisering og lagring av store digitale bildesamlinger, med fokus på skalerbarhet, brukervennlighet og bevaring av originalfiler. Kildematerialet kan være helt offline med dokumentasjon på hvor det befinner seg. Verktøyet skal ikke gripe inn i arbeidsflyten ved bruk av bilderedigeringsverktøy, men fungere et naturlig tillegg.

### 1.2 Bakgrunn og motivasjon
- Eksisterende skyløsninger er kostbare, begrenser personvern og gjør det vanskelig å hente hele samlinger.  
- Profesjonelle verktøy er ofte for avanserte eller kostbare.  
- Manuell lagring fungerer, men krever IT-kompetanse.  

### 1.3 Målgruppe
Systemet er rettet mot privatpersoner og semiprofesjonelle fotografer med store bildesamlinger.  

### 1.4 Begreper
- **Masterbilde**: Originalfil (RAW og/eller JPEG).
- **Kilde**: Katalog som inneholder bilder som skal importeres.  
- **Thumbnail**: Nedskalert versjon for rask visning.  
- **innhold.json**: Fil på roten av en kilde som kan angi regler for import og håndtering

---

## 2. Mål med systemet
- Effektiv organisering av bilder.  
- Redusert lagringsbehov gjennom arkivering og nedskalerte kopier.  
- Intuitivt søk og filtrering.  
- Bevaring av originalitet og unngåelse av duplikater.  
- Fleksibilitet for ulike brukerbehov.  
- Støtte for migrering av kilder til nye medier (offline backup)

---

## 3. Overordnede krav

### 3.1 Funksjonelle krav
- **FR1: Databasehåndtering** – lagre metadata, EXIF-data, og støtte manuell registrering. SQL-database er foretrukket.
- **FR2: Identifikasjon og versjonering** – unike ID-er, thumbnails, nedskalerte versjoner og støtte for redigerte versjoner.  
- **FR3: Brukergrensesnitt** – web-basert søk, tagging, metadata, privat/offentlig-merking og grupperinger.  
- **FR4: Album** – opprette albumer (Markdown-basert), støtte lysbildeserier og fotobøker.  
- **FR5: Import** – import fra katalog, obligatorisk forfatter, notater om lagringsmedium, håndtering av RAW/JPEG, støtte for instruksjonsfil (`innhold.json`).
- **FR6: Backup og migrasjon** - Kildemateriale kan være lagret på medier som går ut på dato, enten som teknologi eller fysisk degradering. Eksempler kan være tape, disketter, cd eller gammel harddisker. Det er hensiktsmessig å flytte materiale over til moderne teknologi, f.eks ny ekstern harddisk. Legge inn støtte for å spore dette med en eller annen form for versjonshåndtering. Selve kildefilene skal ikke endres, bare mediet de ligger på. Ny versjon av en kilde skal ha oppdatert `innhold.json`.

### 3.2 Ikke-funksjonelle krav
- **Ytelse** – håndtere 100k+ bilder (>1 TB), søketid < 1 sek.  
- **Brukbarhet** – intuitivt grensesnitt, støtte for PC og mobil.  
- **Sikkerhet** – tilgangsstyring, kryptering, logging.  
- **Vedlikeholdbarhet** – modulær arkitektur, dokumentert kode, utvidbar database/API.  
- **Teknologiske krav** – API-basert kjerne (Python), web-basert UI (JavaScript), standardiserte verktøy.  

---

## 4. Systemarkitektur (konseptuell)
- **Backend**: database, filstruktur, API for datahåndtering.  
- **Frontend**: web-basert GUI for søk, visning, organisering.  
- **Lagring**: støtte for eksterne medier (offline/online).  

---

## 5. Brukstilfeller
- **UC1: Import av bilder** – bruker velger katalog, systemet registrerer filer, metadata og genererer thumbnails.  
- **UC2: Søk og filtrering** – bruker finner bilder via dato, sted, tagger.  
- **UC3: Album** – bruker oppretter album for deling eller lysbildeserie.  
- **UC4: Versjonering** – bruker legger inn ny versjon etter redigering, koblet via bilde-ID.  

---

## 6. Begrensninger
- Brukeren må organisere kildekataloger manuelt før import.  
- Første versjon støtter JPEG, men diverse råformater skal kunne legges inn i tillegg.  
- Første versjon er enkelbruker, uten samtidige opplastinger.

---

## 7. Fremtidige utvidelser
- AI-basert gjenkjenning og automatisk tagging.  
- Geotagging via karttjenester.  
- Flerbrukerstøtte med samtidige opplastinger
