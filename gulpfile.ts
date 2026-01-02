import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";

import { deleteAsync } from "del";
import { dest, lastRun, parallel, series, src, watch } from "gulp";
import changed from "gulp-changed";
import eslint from "gulp-eslint-new";
import htmlhint from "gulp-htmlhint";
import preserveWhitespace from "gulp-preserve-typescript-whitespace";
import prettyError from "gulp-prettyerror";
import gulpSass from "gulp-sass";
import shell from "gulp-shell";
import stylelint from "gulp-stylelint-esm";
import ts from "gulp-typescript";
import zip from "gulp-zip-plus";
import * as dartSass from "sass";
import { quote } from "shell-quote";


function quoted(strings: TemplateStringsArray, ...params: string[]) {
    const res = []
    for (const [i, str] of strings.raw.entries()) {
        res.push(str);
        if (i < params.length) {
            res.push(quote([params[i]]));
        }
    }
    return res.join("");
}

const sass = gulpSass(dartSass);

const tsProject = ts.createProject("tsconfig.json");

const files = {
    types_ts: "ankiwanikanisync/data/files/types.ts",
    types_py: "ankiwanikanisync/types.py",
    types_base: "ankiwanikanisync/",
    py: [
        "ankiwanikanisync/**/*.py",
        "!ankiwanikanisync/pitch/*.py",
    ],
    py_tests: [
        "tests/**/*.py",
    ],
    db: [
        "ankiwanikanisync/**/*.(json|csv|pickle).xz",
        "ankiwanikanisync/config.json",
        "ankiwanikanisync/manifest.json",
        "ankiwanikanisync/py.typed",
    ],
    // Note: @(data) is a hack to get the correct glob root.
    ts: [
        "ankiwanikanisync/@(data)/**/*.ts",
        "!**/*.d.ts",
    ],
    js: ["ankiwanikanisync/@(data)/**/*.js"],
    scss: ["ankiwanikanisync/@(data)/**/*.scss"],
    media: ["ankiwanikanisync/@(data)/files/**/*.(woff2|png)"],
    html: ["ankiwanikanisync/@(data)/**/*.html"],
    dist: "dist/ankiwanikanisync/",
};

const watchOpts = {
    delay: 200,
};

export function lint_eslint() {
    return src([
        ...files.html,
        ...files.js,
        ...files.ts,
    ], { since: lastRun(lint_eslint) })
      .pipe(prettyError())
      .pipe(eslint())
      .pipe(eslint.format())
      .pipe(eslint.failAfterError());
}

export function lint_htmlhint() {
    return src(files.html, { since: lastRun(lint_htmlhint) })
      .pipe(prettyError())
      .pipe(htmlhint(".htmlhintrc"))
      .pipe(htmlhint.failAfterError());
}

export function lint_stylelint() {
    return src(files.scss, { since: lastRun(lint_stylelint) })
        .pipe(prettyError())
        .pipe(stylelint({}));
}

export function lint_zmypy() {
    return shell.task(["zmypy"])();
}

export async function generate_types() {
    const srcs = [files.types_ts, "munge_types.py", "gulpfile.ts"];
    const src_st = await Promise.all(srcs.map(f => fs.stat(f)));
    const dest_st = await fs.stat(files.types_py);
    if (src_st.every(st => st.mtime <= dest_st.mtime)) {
        return;
    }

    await shell.task([
        quoted`rm -f ${files.types_py}`,
        quoted`ts2python -c3.14 -atoplevel -o ${files.types_base} ${files.types_ts}`,
        quoted`ruff format ${files.types_py}`,
        quoted`ruff check --fix ${files.types_py}`,
        quoted`python munge_types.py ${files.types_py}`,
        quoted`ruff format ${files.types_py}`,
    ])();
}

export function update_accent_data() {
    return shell.task([
        quoted`uv run ./update_accent_data.py accent_data.pickle.xz`,
    ], { cwd: "./ankiwanikanisync/pitch/" })();
}

export function watch_types() {
    return watch([files.types_ts], watchOpts, generate_types);
}

export function watch_eslint() {
    return watch([
        ...files.html,
        ...files.js,
        ...files.ts,
    ], watchOpts, lint_eslint);
}

export function watch_htmlhint() {
    return watch(files.html, watchOpts, lint_htmlhint);
}

export function watch_stylelint() {
    return watch(files.scss, watchOpts, lint_stylelint);
}

export function watch_zmypy() {
    return watch([...files.py, ...files.py_tests], watchOpts, lint_zmypy);
}

export const lint = parallel(lint_eslint, lint_htmlhint, lint_stylelint, lint_zmypy);

export function build_scss() {
    return src(files.scss)
        .pipe(changed(files.dist, { extension: ".css" }))
        // eslint-disable-next-line @typescript-eslint/unbound-method
        .pipe(sass().on("error", sass.logError))
        .pipe(dest(files.dist))
}

export function watch_scss() {
    return watch(files.scss, watchOpts, build_scss);
}

export function build_static() {
    return src([
        ...files.html,
        ...files.js,
        ...files.media,
        ...files.db,
        ...files.py,
    ], { encoding: false })
        .pipe(changed(files.dist))
        .pipe(dest(files.dist));
}

export function build_tf() {
    return src([
        ...files.db,
        ...files.py,
    ]).pipe(changed(files.dist))
      .pipe(dest(files.dist));
}

export function watch_static() {
    return watch([
        ...files.html,
        ...files.js,
        ...files.media,
        ...files.db,
        ...files.py,
    ], watchOpts, build_static);
}

export function build_ts() {
    return src(files.ts).pipe(changed(files.dist, { extension: ".js" }))
                        .pipe(preserveWhitespace.saveWhitespace())
                        .pipe(tsProject())
                        .js
                        .pipe(preserveWhitespace.restoreWhitespace())
                        .pipe(dest(files.dist));
}

export function watch_ts() {
    return watch(files.ts, watchOpts, build_ts);
}

export function clean() {
    return deleteAsync(`${files.dist}**/*`);
}

export const build = series(
    parallel(
        clean,
        generate_types,
    ),
    parallel(
        build_scss,
        build_static,
        build_ts,
        lint,
    ));

export const build_quick = series(
    generate_types,
    parallel(
        build_scss,
        build_static,
        build_ts,
    ));

function getInstallPath(): string {
    if (process.env.ANKIWANIKANISYNC_INSTALL_PATH) {
        return process.env.ANKIWANIKANISYNC_INSTALL_PATH;
    }
    const home = os.homedir();
    let dir: string;
    switch (os.platform()) {
        case "darwin":
            dir = path.join(home, "Library/Application Support/Anki2");
            break;
        case "win32":
            dir = path.join(process.env.APPDATA, "Anki2");
            break;
        default:
            dir = path.join(
                process.env.XDG_DATA_HOME || path.join(home, ".local/share/"),
                "Anki2");
    }
    return path.join(dir, "addons21/ankiwanikanisync");
}

function relativePath(pathStr: string): string {
    return path.relative(import.meta.dirname, pathStr).replace("\\", "/");
}

function doInstall() {
    const destDir = `${relativePath(getInstallPath())}/`;
    return src(`${files.dist}**/*`, { encoding: false })
        .pipe(changed(destDir))
        .pipe(dest(destDir));
}

export const install = series(build, doInstall);

export const install_quick = series(build_quick, doInstall);

function shouldCompress(path: string): boolean {
    return !path.endsWith(".xz");
}

export function export_zip() {
    return src(`${files.dist}**/*`, { encoding: false })
        .pipe(zip("ankiwanikanisync.zip", { compress: shouldCompress }))
        .pipe(dest("./"));
}

export const dist = series(build, export_zip)

export function watch_dist() {
    return watch(`${files.dist}**/*`, watchOpts, doInstall);
}

export const watch_lint = parallel(
    watch_eslint,
    watch_htmlhint,
    watch_stylelint,
    watch_zmypy,
);

export const watch_all = parallel(
    watch_scss,
    watch_static,
    watch_ts,
    watch_dist,
    watch_types,
);
