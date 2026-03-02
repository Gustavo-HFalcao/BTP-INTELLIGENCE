
export enum Page {
  OVERVIEW = 'overview',
  PROJECTS = 'projects',
  CONSTRUCTION = 'construction',
  FINANCE = 'finance',
  OM = 'om',
  AI_CHAT = 'ai_chat',
  ANALYTICS = 'analytics',
  FORECASTS = 'forecasts'
}

export interface ContractRecord {
  projetoInicio: string;
  contrato: string;
  cliente: string;
  terceirizado: string;
  localizacao: string;
  value: number;
  status: string;
  progress: number;
  prazoContratual: string; // Added
  ordemServico: string; // Added
  potencia: string; // Added
  terminoEstimado: string; // Added
}

export interface ActivityRecord {
  id: number;
  fase: string;
  atividade: string;
  critico: string;
  inicio: string;
  termino: string;
  conclusao: number;
  dependencia?: number;
  cliente: string;
  projeto: string;
  responsavel: string;
  contrato: string;
}

export interface FinancialRecord {
  data: string;
  contrato: string;
  projeto: string;
  cliente: string;
  terceirizado: string;
  localizacao: string;
  cockpit: 'Contrato' | 'Terceirizado' | 'Operação';
  marco: string;
  categoria: string;
  servicoContratado: number;
  materialContratado: number;
  servicoRealizado: number;
  materialRealizado: number;
  multa: number;
  justificativas: string;
}

export interface ConstructionRecord {
  data: string;
  contrato: string;
  categoria: 'Civil' | 'Estrutura Metálica' | 'Módulo Solar' | 'Elétrica CC' | 'Inversor' | 'Elétrica CA' | 'Homologação';
  previsto: number; 
  realizado: number;
  comentario: string;
}

export interface OMRecord {
  data: string;
  geracaoPrevista: number;
  energiaInjetada: number;
  kwhCompensado: number;
  kwhAcumulado: number;
  valorFaturado: number;
  gestao: number;
  fatLiquido: number;
  contrato: string;
}
