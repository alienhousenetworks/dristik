import index from './catalog.json';

export interface AeoSectionDefinition {
  number: string;
  part: string;
  title: string;
  checks: string[];
}

export const AEO_PARTS: Array<{ id: string; title: string }> = index.parts;
export const AEO_SECTIONS: AeoSectionDefinition[] = index.sections;
