
export function zip(...args) {
    let len = args[0].length;
    let result = [];
    for (let i = 0; i < len; i++) {
        result.push(args.map(arg => arg[i]));
    }
    return result;
}

export function* chunked(array, n) {
    for (let i = 0; i < array.length; i += n) {
        yield array.slice(i, i + n);
    }
}

export function frag(html) {
    return document.createRange().createContextualFragment(html);
}

export function stripHTML(html) {
    return frag(html).textContent;
}

export let $ = sel => document.querySelector(sel);
export let $$ = sel => document.querySelectorAll(sel);

let htmlMeta = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
};
let htmlRegExp = new RegExp(`[${Object.keys(htmlMeta).join("")}]`, "g");

export let escapeHTML = str => str.replace(htmlRegExp, m0 => htmlMeta[m0]);

export function likelyTypo(expected, typed) {
    let lev = levenshtein(expected, typed);
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
function _min(d0, d1, d2, bx, ay) {
    return d0 < d1 || d2 < d1
        ? d0 > d2
            ? d2 + 1
            : d0 + 1
        : bx === ay
            ? d1
            : d1 + 1;
}

export function levenshtein(a, b) {
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

    let vector = [];

    for (y = 0; y < la; y++) {
        vector.push(y + 1);
        vector.push(a.charCodeAt(offset + y));
    }

    let len = vector.length - 1;

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
