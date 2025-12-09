interface WanaKana {
    ROMANIZATIONS: Record<string, string>;
    TO_KANA_METHODS: Record<string, string>;
    VERSION: string;
    bind: (e: Element) => void;
    isHiragana: (s: string) => boolean;
    isJapanese: (s: string) => boolean;
    isKana: (s: string) => boolean;
    isKanji: (s: string) => boolean;
    isKatakana: (s: string) => boolean;
    isMixed: (s: string) => boolean;
    isRomaji: (s: string) => boolean;
    stripOkurigana: (s: string) => string;
    toHiragana: (s: string) => string;
    toKana: (s: string) => string;
    toKatakana: (s: string) => string;
    toRomaji: (s: string) => string;
    tokenize: (s: string) => string[];
    unbind: (e: Element) => void;
}

declare const wanakana: WanaKana;
export default wanakana;
