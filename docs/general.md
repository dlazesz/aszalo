# Az Aszaló általános célú keresőfelület

**Ez a leírás a felület általános működését tárgyalja. Az egyes adatbázisok specifikus példáihoz és leírásaihoz
rendelkezésre áll külön dokumentáció [itt](mazsola_segedlet.md) és [TODO itt].**

Az Aszaló Sass Bálint [Mazsola](https://github.com/sassbalint/mazsola)
([a magyar igei bővítményszerkezet vizsgálata]( http://corpus.nytud.hu/mazsola)) rendszerének általánosítása
az alapötlet mentén.

A Mazsola bővebben:

[Sass Bálint: "Mazsola" - eszköz a magyar igék bővítményszerkezetének vizsgálatára.
*In: Váradi Tamás (szerk.): Válogatás az I. Alkalmazott Nyelvészeti Doktorandusz Konferencia előadásaiból*,
MTA Nyelvtudományi Intézet, Budapest, 2009, 117-129,](http://www.nytud.hu/alknyelvdok07/proceedings07/Sass.pdf)

## Az alapelv

A korpuszok feldolgozása során a korpuszbeli példamondatokhoz és azok szavaihoz különböző típusú jellemzőket
tudunk rendelni (pl. *szótő*, *szófaj*, *mondatrészi szerep*).
Ezek a jellemzők természetes csoportokat alkotnak (pl. *nyelvtani esetek*, *szintaktikai viszonyok*).
Egyes csoportok több értékkel is szerepelhetnek egy mondaton belül a definíciójuktól függően.
Például több különböző nyelvtani eset képezheti az adott séma *vonzatkeret*ét, de egy 
specifikus nyelvtani eset a legtöbbször maximum egyszer szerepel egy megadott vonzatkereten belül.
A feldolgozott mondatok és a hozzájuk tartozó jellemzők táblázatot alkotnak, mivel minden jellemző egy oszlop,
és az egyes cellákban a jellemzők értékei jelennek meg.
Általában az összes jellemző közül csak keveset tartalmaz egy adott példamondat, ezért a táblázatnak így sok
üres cellája lesz (vagyis az adott táblázat *ritka kitöltöttségű*).

A felület – az adatbázisformába alakított táblázaton – példamondatok keresését és szűrését teszi lehetővé
a jellemzők együttes előfordulása, illetve azok hiánya alapján.
A kapott találatok a szokásos lapos (tabulált) lista formátumhoz képest csoportosítva vannak
egy kiválasztható jellemző érétkeinek fontossági sorrendjében.
Ez egy osztályozást és rangsorolást hoz létre a talált példamondatok között, áttekinthetőbbé téve a keresés eredményét.
Az egyes mondattalálatok tartalmazzák a példamondat mellett annak *azonosító*ját és
a rendezési szempontként megjelölt jellemző *érték*ét. Ezáltal a mondatok könnyen visszakereshetők, továbbvizsgálhatók.

## A jellemzők általános tulajdonságai

A rendszerben a példák, melyek általában mondatok, fixen jelen vannak,
a jellemzők pedig – az *Aszaló* elvének céladatbázisra való alkalmazásával –
szabadon definiálhatók. A továbbiakban körvonalazzuk, hogy milyen szempontok szerint lehet
a jellemzőket a célnak megfelelően definiálni.

### A jellemzők típusai

Az egyes jellemzők lehetnek egyszerűek és összetettek:
   - Az *egyszerű jellemzők* esetén egy szövegmegző áll rendelkezésre. A jellemző értékére tudunk szűrni,
      illetve az értékei alapján osztályozni a találatokat.
   - Az *összetett jellemző* esetében két szövegmező jelenik meg. A **jobboldali mező**ben az adott jellemző 
      (pl. igei argumentum) alosztályát tudjuk meghatározni (pl. különféle esetragok és névutók osztálya). 
    A **baloldali mező**ben pedig igény szerint az alosztályon belüli specifikus érték (pl. az argumentum töve) adható 
    meg.

Rendezési szempont választáskor mindkét esetben az egyes értékek (pl. argumentum töve) szerint osztályoz a rendszer
a jellemző által jelölt osztálytól (pl. az kiválasztott esetragoktól) függően.

Az összetett jellemző **jobboldali mező**je és az egyszerű jellemző **mező**je gépeléskor feldobja a lehetséges elemek 
listáját. Az összetett jellemző **baloldali mező**jénél ez nem történik meg, mert egyfelől meghatározza a **jobboldali 
mező** értéke, másfelől várhatóan túl sok lehetőség közül kellene választani.

### A jellemzők módosítói

Az egyes jellemzők keresési feltételei (az összetett jellemzőnél mindkét mező külön-külön) tovább finomíthatók:
   - A **NOT** opció megadásával a megadott feltétel negálható: Az illeszkedő értékek kihagyásra kerülnek,
      a *nem illeszkedők* kerülnek a találati listába.
   - A **Regex** opció megadásával a szöveges mező reguláris kifejezésként értelmeződik a keresés során,
      így több érték is lefedhető egy keresőszóval. (Ez az opció inaktív nem szöveges értékű, pl. szám mezők esetén.) 
      A reguláris kifejezések használata azért hatékony a lekérdezések során, mert olyan formalizált leíró eszközről
      van szó, amellyel szabványosan, nyelvfüggetlenül és tömör formában definiálhatunk bármilyen karakterszekvenciát,
      vagy akár többet is egyszerre. A karakterek ilyenkor illeszkedhetnek saját magukra,
      de bizonyos karaktereknek és karakterkombinációknak más leíró funkciójuk van.
      A reguláris kifejezésekről bővebben lásd
      ([Sass 2017](http://www.nytud.hu/depts/corpus/resources/sb_kereses_korpuszban.pdf)),
      illetve bonyolultabb lekérdezések teszteléséhez/megírásához segítséget nyújthat
      [ez az oldal](https://regex101.com/).

## A felület működése

### A találati lista oldalakra bontása

Hosszú találati lista esetén a találatokat a rendszer oldalakra bontja,
de a rendezési szempont konkrét értékéhez tartozó csoport mindig teljes egészében egy oldalra kerül.
Az oldalak közötti léptetést a rendezési szempont értékeire kattintva lehet megtenni.
Kék színnel vannak jelölve az aktuális oldalon lévő csoportok és feketével azok,
amelyekre kattintva másik oldalra lépünk a megtekintéshez.

### A találatok mentése

Az adott keresés találatainak listája JSON és TSV formátumban menthető a megfelelő linkre kattintva.
(A JSON formátum esetében jobb egérgombbal a **"link mentése másként"** opciót választva.)
Az összes találat mentésre kerül, nem csak az adott oldalon megjelenítettek, ezért a rendszer lelassulhat.

### Haladó felhasználási módok

1. A webes felület mellett az Aszalónak van egy parancssoros interfésze is, mely ugyanazokat a paramétereket használja,
    mint a webalkalmazás, és nagyobb találati listák offline kigenerálásra is alkalmas.
2. A webes felület JSON formátumú kimenete lehetővé teszi a nem-interaktív használatot REST API formában.
3. A webes felület interaktív felületeinek nyelve testreszabható a konfiguráción keresztül,
    illetve szükség esetén a HTML váz szerkesztésével.
4. Az Aszalóhoz egyszerűen készíthető saját adatbázis TSV formátumból a megfelelő konfiguráció definiálásával.
    Erről angol nyelven külön leírás található a dokumentációban [itt](config.md).
