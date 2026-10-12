import index from './catalog.json';

export interface GeoSectionDefinition {
  number: string;
  part: string;
  title: string;
  checks: string[];
}

export const GEO_PARTS: Array<{ id: string; title: string }> = index.parts;
export const GEO_SECTIONS: GeoSectionDefinition[] = index.sections;
