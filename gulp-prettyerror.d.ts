/* eslint-disable no-unused-vars */
/* globals NodeJS */
declare module "gulp-prettyerror" {
    type CustomFormatter = (e: any, logger: typeof import("gulplog")) => void;
    export default function(formatter?: CustomFormatter): NodeJS.ReadWriteStream;
}
