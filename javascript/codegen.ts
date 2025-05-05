import { CodegenConfig } from "@graphql-codegen/cli";
import { env } from "node:process";

const config: CodegenConfig = {
    schema: [
        {
            "http://graphql_engine:8080/v1/graphql": {
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
