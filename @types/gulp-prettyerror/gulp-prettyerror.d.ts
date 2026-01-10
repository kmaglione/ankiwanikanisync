declare module "gulp-prettyerror" {
    import * as gulplog from "gulplog";

    type ErrorCallback = (error: any, logger: typeof gulplog) => void;

    function PrettyError(errorFormat?: ErrorCallback): NodeJS.ReadWriteStream;

    export default PrettyError;
}
