import type { DeepReadonly } from "./index.js";

// I would like to do
//
//    function zip<T extends unknown[]>(...args: [...T[]]): [...T][] {
//
// but it doesn't do the right thing.
type ZipTuple<T extends unknown[][]> = { [K in keyof T]: T[K][number] };
export function zip<T extends unknown[][]>(...args: T): ZipTuple<T>[] {
    const len = args[0].length;
    const result = [];
    for (let i = 0; i < len; i++) {
        result.push(args.map(arg => arg[i]) as ZipTuple<T>);
    }
    return result;
}

export function* chunked<T>(array: T[], n: number): Generator<T[], void, void> {
    for (let i = 0; i < array.length; i += n) {
        yield array.slice(i, i + n);
    }
}

const SPACE = /\s+/g;
export function split(str: string, pat: string | RegExp = SPACE): string[] {
    if (pat === SPACE) {
        str = str.trim();
    }
    return str ? str.split(pat) : [];
}

export function deepFreeze<T extends object>(obj: T): DeepReadonly<T> {
    Object.freeze(obj);
    for (const val of Object.values(obj)) {
        if (typeof val === "object" && obj != null) {
            deepFreeze(val);
        }
    }
    return obj as DeepReadonly<T>;
}

export function frag(html: string) {
    return document.createRange().createContextualFragment(html);
}

export function stripHTML(html: string) {
    return frag(html).textContent;
}

/* globals NodeListOf */
export function $<T extends Element = HTMLElement>(sel: string): T {
    return document.querySelector(sel);
}
export function $$<T extends Element = HTMLElement>(sel: string): NodeListOf<T> {
    return document.querySelectorAll(sel);
}

const htmlMeta: Record<string, string> = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
} as const;
const htmlRegExp = new RegExp(`[${Object.keys(htmlMeta).join("")}]`, "g");

export const escapeHTML = (str: string) => str.replace(htmlRegExp, m0 => htmlMeta[m0]);

export function likelyTypo(expected: string, typed: string): boolean {
    const lev = levenshtein(expected, typed);
    switch (expected.length) {
    case 0:
    case 1:
        return expected == typed;
    case 2:
    case 3:
        return lev < 2;
    default:
        return lev < 3;
    }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function assert(condition: any, msg?: string): asserts condition {
    if (!condition) {
        throw new Error(msg);
    }
}

export function assertNever(msg?: string): never {
    throw new Error(msg);
}
/* c8 ignore start */
/*
 * For the following:
 *
 * MIT License
 *
 * Copyright (c) 2017 Gustaf Andersson
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
/* istanbul ignore next */
function _min(d0: number, d1: number, d2: number, bx: number, ay: number) {
    return d0 < d1 || d2 < d1
        ? d0 > d2
            ? d2 + 1
            : d0 + 1
        : bx === ay
            ? d1
            : d1 + 1;
}

/* istanbul ignore next */
export function levenshtein(a: string, b: string): number {
    if (a === b) {
        return 0;
    }

    if (a.length > b.length) {
        [a, b] = [b, a];
    }

    let la = a.length;
    let lb = b.length;

    while (la > 0 && (a.charCodeAt(la - 1) === b.charCodeAt(lb - 1))) {
        la--;
        lb--;
    }

    let offset = 0;

    while (offset < la && (a.charCodeAt(offset) === b.charCodeAt(offset))) {
        offset++;
    }

    la -= offset;
    lb -= offset;

    if (la === 0 || lb < 3) {
        return lb;
    }

    let x = 0;
    let y;
    let d0;
    let d1;
    let d2;
    let d3;
    let dd;
    let dy;
    let ay;
    let bx0;
    let bx1;
    let bx2;
    let bx3;

    const vector = [];

    for (y = 0; y < la; y++) {
        vector.push(y + 1);
        vector.push(a.charCodeAt(offset + y));
    }

    const len = vector.length - 1;

    for (; x < lb - 3;) {
        bx0 = b.charCodeAt(offset + (d0 = x));
        bx1 = b.charCodeAt(offset + (d1 = x + 1));
        bx2 = b.charCodeAt(offset + (d2 = x + 2));
        bx3 = b.charCodeAt(offset + (d3 = x + 3));
        dd = (x += 4);
        for (y = 0; y < len; y += 2) {
            dy = vector[y];
            ay = vector[y + 1];
            d0 = _min(dy, d0, d1, bx0, ay);
            d1 = _min(d0, d1, d2, bx1, ay);
            d2 = _min(d1, d2, d3, bx2, ay);
            dd = _min(d2, d3, dd, bx3, ay);
            vector[y] = dd;
            d3 = d2;
            d2 = d1;
            d1 = d0;
            d0 = dy;
        }
    }

    for (; x < lb;) {
        bx0 = b.charCodeAt(offset + (d0 = x));
        dd = ++x;
        for (y = 0; y < len; y += 2) {
            dy = vector[y];
            vector[y] = dd = _min(dy, d0, dd, bx0, vector[y + 1]);
            d0 = dy;
        }
    }

    return dd;
}
/* c8 ignore stop */
