import { CodegenConfig } from "@graphql-codegen/cli";
import { env } from "node:process";

const graphql_engine_hostname: string = env["GRAPHQL_HOST"] || "graphql_engine";
const graphqlEngineUrl: string = "http://" + graphql_engine_hostname + ":8080/v1/graphql";

const config: CodegenConfig = {
    schema: [
        {
            [graphqlEngineUrl]: {
                headers: {
                    "x-hasura-admin-secret": env["HASURA_GRAPHQL_ADMIN_SECRET"],
                } as any,
            },
        },
    ],
    documents: ["src/**/*.{ts,tsx}"],
    generates: {
        "./src/__generated__/": {
            preset: "client",
            plugins: [],
            presetConfig: {
                gqlTagName: "gql",
            },
            config: {
                useTypeImports: true,
                scalars: {},
            },
        },
    },
    ignoreNoDocuments: false,
    noSilentErrors: true,
    verbose: true,
    debug: true,
    emitLegacyCommonJSImports: false,
};

export default config;
