/* globals _ */
import wanakana from "./_wanakana.min.js";
import { $$, $, assert, escapeHTML, frag, likelyTypo, split, stripHTML } from "./_wk3_util.js";
import type { RelatedSubject } from "./types.js";

function setLangJa(elem: Element) {
    elem.setAttribute("lang", "ja");
}

const tagTitles: Record<string, string> = {
    "kanji": "Kanji",
    "radical": "Radical",
    "vocabulary": "Vocabulary",
    "reading": "Reading",
};

function jaTag(tag: string, contents: string) {
    return `<${tag} lang="ja" title="${tagTitles[tag] || ""}">${
        contents
    }</${tag}>`
}

function hide(elem: HTMLElement, hidden: boolean = true) {
    elem.classList[hidden ? "add" : "remove"]("hidden");
}

export function setupBack() {
    /* SCRIPT: Slice meanings and insert into the Meaning Section. */
    $(`#meaning-title`).append(_.Card_Type === "Radical" ? "Name" : "Meaning");

    const [primary, ...alternative] = split(_.Meaning, ",");

    {
        const div = $("#meanings");
        div.insertAdjacentHTML("beforeend", `<p><b>Primary</b> ${primary}</p>`)

        if (alternative.length) {
            div.insertAdjacentHTML("beforeend", `<p><b>Alternative</b> ${alternative.join(", ")}</p>`);
        }

        if (_.Word_Type.length) {
            div.insertAdjacentHTML("beforeend", `<p><b>Word Type</b> ${_.Word_Type}</p>`);
        }
    }

    for (const elem of $$(":is(#onyomi-readings, #kunyomi-readings, #nanori-readings):has( reading)")) {
        elem.classList.add("readings-primary");
    }

    /* SCRIPT: Disable unused Reading divisions. */
    hide($("#onyomi-readings"), !_.Reading_Onyomi);
    hide($("#kunyomi-readings"), !_.Reading_Kunyomi);
    hide($("#nanori-readings"), !_.Reading_Nanori);

    /* SCRIPT: Disable unused Hint divisions. */
    hide($("#meaning-hint"), !_.Meaning_Hint);
    hide($("#reading-hint"), !_.Reading_Hint);

    /* SCRIPT: Slice and add Context Patterns  */
    const combinations = _.Context_Patterns;

    function addCombinations(name: string) {
        const div = $("#common-word-combinations");
        for (const {ja, en} of combinations[name]) {
            div.append(frag(`<p class="combination">
                ${jaTag("ja", ja)}<br>
                ${en}
            </p>`))
        }
    }

    function onButtonClick(event: Event) {
        for (const elem of $$(".button")){
            elem.classList.remove("clicked");
        }
        assert(event.target instanceof Element, "Unexpected element type");
        event.target.classList.add("clicked");

        for (const elem of $$(".combination")) {
            elem.remove();
        }
        addCombinations(event.target.getAttribute("name"));
    }

    const names = Object.keys(combinations);
    for (const name of names){
        const element = document.createElement("div");
        element.innerHTML = `
            <button class="button" lang="ja" name="${name}">${
                name
            }</button><br>`;
        element.firstElementChild.addEventListener("click", onButtonClick);
        $("#patterns-of-use").appendChild(element);
    }

    if (names.length === 0) {
        $("#context-patterns").textContent = " ";
    } else {
        $(`.button[name='${names[0]}']`).click();
    }

    /* SCRIPT: Slice and add context sentences. */
    if (["Vocabulary", "Kana Vocabulary"].includes(_.Card_Type)) {
        const div = $("#context-sentences");

        for (const {en, ja} of _.Context_Sentences) {
            div.append(frag(`<p>${jaTag("ja", ja)}<br>${en}</p>`));
        }
    }

    /* SCRIPT: Disable divisions. */
    switch (_.Card_Type) {
        case "Radical":
            hide($("#section-reading"));
            hide($("#section-context"));
            hide($("#section-radical-combination"));
            hide($("#section-found-in-vocabulary"));
            break;
        case "Kanji":
            hide($("#section-context"));
            break;
        case "Vocabulary":
        case "Kana Vocabulary":
            hide($("#section-radical-combination"));
            hide($("#section-found-in-vocabulary"));
    }

    /* SCRIPT: Populate Box Characters (Found in Kanji, Visually Similar Kanji and Kanji Composition). */
    function setRelated(title: string, related: readonly RelatedSubject[]) {
        if (related.length !== 0) {
            $("#box-title").textContent = title;

            for (const {characters, reading, meaning} of related) {
                $("#box-container").appendChild(frag(
                    `<div id="box-character" lang="ja">
                        ${characters}
                        <div id="box-meaning">
                            ${reading}<br>
                            <span lang="en">${meaning}</span>
                        </div>
                    </div>`));
            }
        } else {
            $("#section-box").remove();
        }
    }
    switch (_.Card_Type) {
      case "Radical":
        setRelated("Found In Kanji", _.Found_in);
        break;
      case "Kanji":
        setRelated("Visually Similar Kanji", _.Similar);
        break;
      case "Vocabulary":
      case "Kana Vocabulary":
        setRelated("Kanji Composition", _.Comps);
        break;
      default:
        /* istanbul ignore next */
        $("#section-box").remove();
    }

    /* SCRIPT: Add Phonetic-Semantic Composition Characters. */
    const CDOT = "・";
    switch (_.Card_Type) {
      case "Kanji":
      case "Radical": {
        const data = _.Keisei;
        const description = $("#phonetic-semantic-description");
        switch (data.type) {
          case "compound":
          case "phonetic": {
            switch (data.type) {
              case "compound":
                description.innerHTML = `
                    The kanji ${jaTag("kanji", _.Characters)} was created using
                    semantic-phonetic composition.<br>
                    <br>
                    The phonetic component is
                    <span lang="ja">「${jaTag("ja", data.component)}」</span> with the ON
                    reading(s) <span lang="ja">「${jaTag("ja", data.readings.join(CDOT))}」</span>
                    (including rare ones), and the semantic component is
                    <span lang="ja">「${jaTag("ja", data.semantic)}」</span>.<br>`;
                break;
              case "phonetic":
                if (_.Card_Type === "Kanji") {
                    description.innerHTML = `
                        The kanji ${jaTag("kanji", _.Characters)} is used as a phonetic
                        component in other compounds.<br>
                        Its ON reading(s) are
                        <span lang="ja">「${jaTag("ja", data.readings.join(CDOT))}」</span>.<br>`;
                } else {
                    description.innerHTML = `
                        The radical ${jaTag("radical", _.Characters)} is used as a phonetic
                        component in other compounds.<br>
                        Its ON reading(s) are
                        <span lang="ja">「${jaTag("ja", data.readings.join(CDOT))}」</span>.<br>`;
                }
            }

            {
                const div = $("#phonetic-container");
                div.appendChild(frag(
                    `<div id="phonetic-character" lang="ja">
                        ${data.component}
                        <div id="box-meaning">
                            ${data.readings[0]}<br>
                            <span lang="en">Phonetic</span>
                        </div>
                    </div>`));
                if (data.radical) {
                    div.appendChild(frag(
                        `<div id="radical-character" lang="ja">
                            ${data.component}
                            <div id="box-meaning">
                                ${data.readings[0]}<br>
                                <span lang="en">${data.radical}</span>
                            </div>
                        </div>`));
                }
                if (data.kanji) {
                    div.appendChild(frag(
                        `<div id="box-character" lang="ja">
                            ${data.component}
                            <div id="box-meaning">
                                ${data.kanji[1]}<br>
                                <span lang="en">${data.kanji[0]}</span>
                            </div>
                        </div>`));
                }
            }
            const div = $("#compound-container");
            for (const comp of data.compounds) {
                div.appendChild(frag(
                    `<div id="box-character" lang="ja">
                        ${comp.character}
                        <div id="box-meaning">
                            ${comp.reading}<br>
                            <span lang="en">${comp.meaning}</span>
                        </div>
                    </div>`));
            }
            break;
          }
          case "unprocessed":
            description.innerHTML = `
                The kanji ${jaTag("kanji", _.Characters)} has not been added to the WK
                Userscripts Keisei DB yet.
                Please wait for a future version.<br>`;
            break;
          case "nonradical":
            description.innerHTML = `
                The radical ${jaTag("radical", _.Characters)} is not considered a
                phonetic mark.<br>`;
            break;
          case "unknown":
            description.innerHTML = `
                The kanji ${jaTag("kanji", _.Characters)} has an unknown or contested origin,
                or its phonetic mark is too obscure to be useful.
                Stay tuned for more information in future versions of WK Userscripts
                Keisei.`;
            break;
          case null:
            hide($("#section-phonetic-semantic"));
            break;
          default:
            description.innerHTML = `
                The kanji ${jaTag("kanji", _.Characters)} is not considered a
                semantic-phonetic composition.<br>
                Note: ${data.type}<br>`;
        }
        break;
      }
      default:
        hide($("#section-phonetic-semantic"));
    }

    /* SCRIPT: Add Radical Combination Characters. */
    const compsLength = Object.keys(_.Comps).length;
    for (const [i, {characters, meaning}] of _.Comps.entries()) {
        {
            const element = document.createElement("div");
            element.style.display = "flex";
            element.style.alignItems = "center";

            element.innerHTML = `
                <radical-combination lang="ja">
                    <div>${characters}</div>
                </radical-combination>
                <div>
                    ${meaning.substring(0, 15)}
                </div>`;
            $("#combination").appendChild(element);
        }

        if (i + 1 != compsLength) {
            $("#combination").appendChild(frag(
                "<p><div class=combination-plus><b>+<b/></div></p>"));
        }
    }

    /* SCRIPT: Add Found in Vocabulary Characters. */
    for (const {characters, reading, meaning} of _.Found_in) {
        $("#found-in-vocabulary-container").appendChild(frag(
            `<div class="found-in-vocabulary-box" lang="ja">
                <div class="found-in-voc">
                    ${characters}
                </div>
                <div class="found-in-voc-reading">
                    ${reading}<br>
                    <span lang="en">${meaning}</span>
                </div>
            </div>`));
    }

    if (_.Found_in.length == 0) {
        hide($("#section-found-in-vocabulary"));
    }

    /* SCRIPT: Check the answer  */
    const mangleAnswer = (ans: string) => ans.toLowerCase().replace("'", "");

    const typeans = $("#typeans");
    let typedAnswer: string, typedAnswerLower: string;
    if (typeans) {
        typedAnswer = "";
        typeans.innerHTML = typeans.innerHTML.replace(/<br.*/, "");
        typeans.querySelectorAll(".typeGood, .typeBad").forEach((e) => {
            if (e.textContent == "-") return;
            typedAnswer += e.textContent;
        });
        typedAnswerLower = mangleAnswer(typedAnswer);
    } else {
        typedAnswerLower = "";
    }

    const meaningWhitelist = new Set(split(_.Meaning_Whitelist.toLowerCase(), ", "));
    const readingWhitelist = new Set(split(_.Reading_Whitelist.toLowerCase(), ", "));
    let correctAnswers = new Set<string>();
    const correctText = $("#correct");

    switch (_.Card) {
      case "Meaning": {
        const capitalize = (iter: Iterable<string>): string[] => Array.from(iter,
            (elem: string): string => elem.replace(/(^| )\w/g, c => c.toUpperCase()));

        correctAnswers = new Set(split(_.Meaning.toLowerCase(), ", "));
        const [meaning, ...alternatives] = capitalize(correctAnswers);

        const accepted = meaningWhitelist.difference(correctAnswers);
        correctAnswers = correctAnswers.union(accepted);

        correctText.innerHTML = `Primary: <b>${meaning}</b>`;
        if (alternatives.length) {
            correctText.insertAdjacentHTML("beforeend", `<br>
                Alternative: <b>${alternatives.join(", ")}</b>`);
        }
        if (accepted.size) {
            correctText.insertAdjacentHTML("beforeend", `<br>
                <details>
                    <summary>Accepted:</summary>
                    <b>${capitalize(accepted).join(", ")}</b>
                </details>`);
        }
        $<HTMLDetailsElement>("#section-meaning > details").open = true;
        break;
      }
      case "Reading": {
        correctAnswers = readingWhitelist;
        const items = Array.from(correctAnswers, x => jaTag("reading", x));
        correctText.innerHTML = items.join(" ");

        $("#section-phonetic-semantic").after($("#section-meaning"));
        $<HTMLDetailsElement>("#section-reading > details").open = true;
      }
    }

    let blacklist = new Set();
    if (_.Card === "Meaning") {
        blacklist = new Set(split(_.Meaning_Blacklist, ", ")
                                   .map(s => s.toLowerCase()));
    }

    function checkTypos(answers: Set<string>,
                        expected: Set<string>,
                        mangle = (x: string): string => x) {
        let found = 0;
        const typos = $("#typos");
        for (const ans of answers) {
            if (blacklist.has(ans)) {
                continue;
            }
            for (const exp of expected) {
                if (likelyTypo(mangle(exp), mangle(ans))) {
                    found++;
                    typos.insertAdjacentHTML("beforeend", `
                        <div class="typo">
                            Did you mean <span class="typo-expected">${escapeHTML(exp)}</span>
                            instead of <span class="typo-ans">${escapeHTML(ans)}</span>?
                        </div>
                    `)
                }
            }
        }
        if (found) {
            hide(typos, false);
        }
    }

    if (typedAnswerLower !== "") {
        const answerDiv = document.createElement("div");
        answerDiv.setAttribute("id", "typeans");
        answerDiv.textContent = typedAnswer;
        answerDiv.classList.add(`typeans-${_.Card}`)
        if (_.Card == "Reading") {
            setLangJa(answerDiv);
        }
        $("#typeans").replaceWith(answerDiv);

        correctAnswers = new Set(
            Array.from(correctAnswers, a => mangleAnswer(stripHTML(a))));

        const answers = new Set<string>(split(typedAnswerLower, /[、,]\s*/));
        if (answers.isSubsetOf(correctAnswers)) {
            answerDiv.classList.add("correct");
        } else {
            answerDiv.classList.add("incorrect");

            const mangle = _.Card == "Reading" ? wanakana.toRomaji : (x: string) => x;
            checkTypos(answers, correctAnswers, mangle);
        }
    } else {
        hide($("#input"));
    }

    /* Generate tooltips for tags that came from card field substitutions */
    for (const [tag, title] of Object.entries(tagTitles)) {
        for (const elem of $$(`${tag}:not([title])`)) {
            elem.setAttribute("title", title);
            setLangJa(elem);
        }
    }

    for (const tag of $$("ja:not([lang])")) {
        setLangJa(tag)
    }
}
