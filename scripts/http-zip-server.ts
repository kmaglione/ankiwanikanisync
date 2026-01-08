import * as fs from "fs/promises";
import http from "http";
import type { AddressInfo } from "net";
import { parseArgs } from "node:util";

import mime from "mime";
import StreamZip from "node-stream-zip";

const args = parseArgs({
    allowPositionals: true,
    options: {
        host: {
            type: "string",
            short: "h",
            default: "localhost",
        },
        port: {
            type: "string",
            short: "p",
            default: "0",
        },
    },
    strict: true,
});

class Server {
    zip: StreamZip.StreamZipAsync;
    rootURL: string | null;
    _server: http.Server;

    constructor(zip: StreamZip.StreamZipAsync) {
        this.zip = zip;

        this._server = http.createServer((req, res) => {
            this.handleRequest(req, res).catch(error => {
                console.error(error)
                res.writeHead(500);
                res.end("500 Internal server error");
            });
        });
    }

    async handleRequest(req: http.IncomingMessage, res: http.ServerResponse<http.IncomingMessage>) {
        if (req.method !== "GET" || !req.url) {
            res.writeHead(405);
            res.end("405 Method not allowed");
            return;
        }

        let { pathname } = URL.parse(req.url, `http://${req.headers.host}/`);
        if (pathname.endsWith("/")) {
            pathname += "index.html";
        }

        console.log(`Request: ${pathname}`);

        let stream;
        try {
            stream = await this.zip.stream(pathname.substring(1));
        } catch (_) {
            console.log(` [404] : ${pathname}`);
            res.writeHead(404);
            res.end("404 Not found");
            return;
        }

        const mimeType = mime.getType(pathname);

        res.writeHead(200, { "Content-Type": mimeType });
        stream.pipe(res);
    }

    async listen(host: string, port: number) {
        await new Promise(resolve => {
            this._server.listen(port, host, () => resolve(null));
        });

        const actualPort = (this._server.address() as AddressInfo).port;
        this.rootURL = `http://${args.values.host}:${actualPort}/`;
    }
}

async function main(): Promise<number> {
    const port = parseInt(args.values.port);
    if (String(port) !== args.values.port) {
        console.error("Error: Expected an integer for --port");
        return 1;
    }

    if (args.positionals.length !== 1) {
        console.error("Error: Expected one argument containing the path to a zip file");
        return 1;
    }

    const zipPath = args.positionals[0];

    let st;
    try {
        st = await fs.stat(zipPath);
    } catch (_) {
        // Ignore
    }
    if (!st || !st.isFile()) {
        console.error(`Error: ${zipPath} is not a file`);
        return 1;
    }

    const zip = new StreamZip.async({ file: zipPath });
    try {
        await zip.entriesCount;
    } catch (e) {
        console.error(`Error opening zip archive ${zipPath}: ${(e as Error).message}`);
        return 1;
    }

    const server = new Server(zip);
    await server.listen(args.values.host, port);

    console.log(`Listening on ${server.rootURL}`)
    return 0;
}

main().then(rv => {
    if (rv !== 0) {
        process.exit(rv);
    }
}, err => {
    console.error(err);
    process.exit(1);
});
