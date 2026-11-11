import bundle from "../generated/bundle.json";
import { Case, Taxonomy } from "./types";
import Ajv from "ajv/dist/2020";
import schema from "../../../contracts/result.schema.json";
const validate = new Ajv({ strict: false }).compile(schema);
for (const result of bundle.results) {
  if (!validate(result))
    throw new Error("Invalid triage artifact: " + JSON.stringify(validate.errors));
}
export const cases = bundle.cases as unknown as Case[];
export const taxonomy = bundle.taxonomy as Taxonomy;
export const manifest = bundle.manifest;
