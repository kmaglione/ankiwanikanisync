import type { ResultPromise } from "execa";
import * as execa from "gulp-execa";

function quoted(strings: TemplateStringsArray, ...params: string[]) {
    const res = [];
    for (const [i, str] of strings.raw.entries()) {
        res.push(str);
        if (i < params.length) {
            res.push(params[i].replace(/\s/g, "\\$&"));
        }
    }
    return res.join("");
}

type ExecFn<T> = (strings: TemplateStringsArray, ...params: string[]) => ResultPromise<T>;
export function exec(strings: TemplateStringsArray, ...params: string[]): ResultPromise<object>;
export function exec<T = object>(options: T): ExecFn<T>;

export function exec<T = object>(strings: TemplateStringsArray | T, ...params: string[]) {
    if (Array.isArray(strings) && "raw" in strings) {
        return execa.exec(quoted(strings as TemplateStringsArray, ...params));
    }
    const options = strings as T;
    return function (strings: TemplateStringsArray, ...params: string[]) {
        return execa.exec(quoted(strings, ...params), options);
    };
}
