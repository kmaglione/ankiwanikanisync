#!/usr/bin/env node
import * as fs from "fs/promises";

import { makeBadge as makeBadgeSVG } from "badge-maker";
import type { Format } from "badge-maker";

const DATA_SVG = "data:image/svg+xml;base64,";
const ICONS: Record<string, string> = {
    mocha: '<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>Mocha</title><path d="M13.325 0c-.907 1.116-2.442 2.302-.768 4.814.558.628.838 1.953.768 2.372 0 0 2.512-1.464.977-4.116-.907-1.395-1.326-2.582-.977-3.07zm-2.79 2.582c-.628.767-1.605 1.535-.489 3.279.35.349.489 1.256.489 1.535 0 0 1.673-.978.627-2.792-.628-.907-.906-1.743-.627-2.022zm-5.094 6a.699.699 0 0 0-.697.698c0 2.372.349 10.535 3.837 14.512.14.139.28.208.489.208h5.86c.21 0 .35-.069.489-.208 3.488-3.908 3.837-12.07 3.837-14.512a.7.7 0 0 0-.698-.699H12zm2.023 2.163h9.21c.349 0 .697.278.697.697 0 1.953-.348 7.465-2.72 10.326-.21.14-.35.208-.559.208H9.976a.633.633 0 0 1-.488-.208c-2.372-2.79-2.652-8.373-2.722-10.326 0-.35.28-.697.698-.697zm8.792 4.744s-.071.627-1.745 1.255c-2.303.837-6.348.28-6.348.28.349 1.465.906 2.86 1.743 3.907.07.14.28.209.419.209h3.489c.14 0 .279-.07.418-.209 1.186-1.395 1.745-3.558 2.024-5.442z" fill="white"/></svg>',
    pytest: '<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>Pytest</title><path d="M2.6152 0v.8867h3.8399V0zm5.0215 0v.8867h3.8418V0zm4.957 0v.8867h3.8418V0zm4.9356 0v.8867h3.8418V0zM2.4473 1.8945a.935.935 0 0 0-.9356.9356c0 .517.4185.9375.9356.9375h19.1054c.5171 0 .9356-.4204.9356-.9375a.935.935 0 0 0-.9356-.9356zm.168 2.8477V24H6.455V4.7422zm5.0214 0V20.543h3.8418V4.7422zm4.957 0V15.291h3.8497V4.7422zm4.9356 0v6.4941h3.8418V4.7422z" fill="#0A9EDC"/></svg>',
    wdio: '<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>WebdriverIO</title><path d="M1.875 0C0.836 0 0 0.836 0 1.875v20.25C0 23.164 0.836 24 1.875 24h20.25C23.164 24 24 23.164 24 22.125V1.875C24 0.836 23.164 0 22.125 0ZM2.25 6H3V18H2.25ZM9.335 6H10.125L5.29 18H4.499ZM16.125 6c3.314 0 6 2.686 6 6 0 3.314-2.686 6-6 6-3.314 0-6-2.686-6-6 0-3.314 2.686-6 6-6zm0 0.75c-2.899 0-5.25 2.351-5.25 5.25 0 2.899 2.351 5.25 5.25 5.25 2.899 0 5.25-2.351 5.25-5.25 0-2.899-2.351-5.25-5.25-5.25z" fill="white"/></svg>',
};

const ICON_URLS: Record<string, string> = {};
for (const [name, svg] of Object.entries(ICONS)) {
    ICON_URLS[name] = DATA_SVG + Buffer.from(svg, "utf-8").toString("base64");
}

type Outcome = "success" | "failure" | "cancelled" | "skipped";
interface Step {
    conclusion: Outcome;
    outcome: Outcome;
    outputs: Record<string, string>;
}
const steps = JSON.parse(process.env.STEPS) as Record<string, Step>;

interface BadgeOpts {
    steps: (keyof typeof steps)[];
    icon?: string;
    iconSVG?: string;
    label: string;
}

interface Badge {
    label: string;
    labelColor: string;
    message: string;
    color?: string;
    isError?: boolean;
    namedLogo?: string;
    logoBase64?: string;
    svgFile: string;
}

async function makeBadge(opts: BadgeOpts): Promise<Badge> {
    const statuses = opts.steps.map(s => steps[s].outcome);

    const badge: Badge = {
        label: opts.label,
        labelColor: "#343b42",
        message: statuses.includes("failure")
            ? "failing"
            : (["skipped", "cancelled"] as Outcome[]).some(s => statuses.includes(s))
                ? "skipped"
                : "passing",
        svgFile: `badge-${opts.label}.svg`,
    };

    if (opts.icon) {
        badge.namedLogo = opts.icon;
    }
    if (opts.iconSVG) {
        badge.logoBase64 = opts.iconSVG;
    }

    if (badge.message === "failing") {
        badge.isError = true;
        badge.color = "red";
    } else if (badge.message === "skipped") {
        badge.color = "inactive";
    } else {
        badge.color = "#2dbb4e";
    }

    const format: Format = {
        label: badge.label,
        labelColor: badge.labelColor,
        message: badge.message,
        color: badge.color,
    };
    if (badge.logoBase64) {
        format.logoBase64 = badge.logoBase64;
    }
    const svg = makeBadgeSVG(format);

    await fs.writeFile(badge.svgFile, svg);

    return badge;
}

const badges = [
    await makeBadge({
        label: "Pytest",
        steps: ["pytest"],
        icon: "pytest",
        iconSVG: ICON_URLS.pytest,
    }),
    await makeBadge({
        label: "WDIO",
        steps: ["wdio"],
        icon: "WebdriverIO",
        iconSVG: ICON_URLS.wdio,
    }),
    await makeBadge({
        label: "Mocha",
        steps: ["mocha"],
        icon: "Mocha",
        iconSVG: ICON_URLS.mocha,
    }),
    await makeBadge({
        label: "lint",
        steps: ["ruff", "eslint", "stylelint", "htmlhint", "zmypy", "build_ts"],
    }),
];

const result: Record<string, Badge> = {};
for (const badge of badges) {
    result[badge.label] = badge;
}

await fs.writeFile(process.env.GITHUB_OUTPUT, `badges=${JSON.stringify(result)}\n`);
