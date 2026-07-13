// Single source of truth for exam names and subjects.
// Always use these constants — never type exam names as raw strings.

export const EXAMS = [
  { value: 'JEE Main',   label: 'JEE Main' },
  { value: 'JEE Advanced', label: 'JEE Advanced' },
  { value: 'NEET',       label: 'NEET' },
  { value: 'CUET',       label: 'CUET' },
] as const

export type ExamName = (typeof EXAMS)[number]['value']

export const SUBJECTS = [
  { value: 'physics',     label: 'Physics' },
  { value: 'chemistry',   label: 'Chemistry' },
  { value: 'mathematics', label: 'Mathematics' },
  { value: 'biology',     label: 'Biology' },
  { value: 'english',     label: 'English' },
  { value: 'hindi',       label: 'Hindi' },
] as const

export type SubjectName = (typeof SUBJECTS)[number]['value']

// Which subjects are relevant for each exam
export const EXAM_SUBJECTS: Record<string, SubjectName[]> = {
  'JEE Main':      ['physics', 'chemistry', 'mathematics'],
  'JEE Advanced':  ['physics', 'chemistry', 'mathematics'],
  'NEET':          ['physics', 'chemistry', 'biology'],
  'CUET':          ['physics', 'chemistry', 'mathematics', 'biology', 'english', 'hindi'],
}

/** Returns the subjects available for a given exam (or all if exam not recognised). */
export function subjectsForExam(exam: string): typeof SUBJECTS[number][] {
  const allowed = EXAM_SUBJECTS[exam]
  if (!allowed) return [...SUBJECTS]
  return SUBJECTS.filter((s) => allowed.includes(s.value as SubjectName))
}
