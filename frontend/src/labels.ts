export const SCALE = [
  { range: '0', label: 'Não demonstra', min: 0, max: 0 },
  { range: '1-2', label: 'Muito baixo', min: 1, max: 2 },
  { range: '3-4', label: 'Baixo', min: 3, max: 4 },
  { range: '5-6', label: 'Moderado', min: 5, max: 6 },
  { range: '7-8', label: 'Bom', min: 7, max: 8 },
  { range: '9-10', label: 'Excelente', min: 9, max: 10 },
]

export function scaleLabel(score: number): string {
  return SCALE.find((s) => score >= s.min && score <= s.max)?.label ?? ''
}

export const DEV_TYPES: Record<string, string> = {
  curso: 'Curso',
  treinamento_interno: 'Treinamento interno',
  mentoria: 'Mentoria',
  acompanhamento: 'Acompanhamento',
  atividades_praticas: 'Atividades práticas',
  projeto_desafio: 'Projeto desafio',
  certificacao: 'Certificação',
  outro: 'Outro',
}

export const STAY_IN_ROLE: Record<string, string> = {
  sim: 'Sim',
  nao: 'Não',
  nao_sei: 'Não sei',
}

export const TIMEFRAMES: Record<string, string> = {
  ate_3m: 'Até 3 meses',
  '3_6m': '3 a 6 meses',
  '6_12m': '6 a 12 meses',
  mais_12m: 'Mais de 12 meses',
}

export const STATUS_LABEL: Record<string, string> = {
  pendente: 'Pendente',
  rascunho: 'Rascunho',
  completo: 'Completo',
}

export const TYPE_LABEL: Record<string, string> = {
  auto: 'Autoavaliação',
  gestor: 'Avaliação como gestor',
  rh: 'Avaliação como RH',
}
