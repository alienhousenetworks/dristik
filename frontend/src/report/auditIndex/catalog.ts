import index from './catalog.json';
import { AuditSectionDefinition } from './types';

export const AUDIT_PARTS: Array<{ id: string; title: string }> = index.parts;
export const AUDIT_SECTIONS: AuditSectionDefinition[] = index.sections;
