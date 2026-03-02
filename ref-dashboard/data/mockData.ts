
import { ContractRecord, ActivityRecord, FinancialRecord, ConstructionRecord, OMRecord } from '../types';

export const contracts: ContractRecord[] = [
  { 
    projetoInicio: '2024-09-01', 
    contrato: 'BOM010-24', 
    cliente: 'Escola A', 
    terceirizado: 'Empresa C', 
    localizacao: 'Recife, PE',
    value: 2500000,
    status: 'Em Execução',
    progress: 45,
    prazoContratual: '120 dias',
    ordemServico: 'OS-1092',
    potencia: '100 kWp',
    terminoEstimado: '2025-01-15'
  },
  { 
    projetoInicio: '2024-10-15', 
    contrato: 'BOM011-24', 
    cliente: 'Hospital B', 
    terceirizado: 'Empresa D', 
    localizacao: 'Salvador, BA',
    value: 4800000,
    status: 'Em Execução',
    progress: 12,
    prazoContratual: '200 dias',
    ordemServico: 'OS-2044',
    potencia: '350 kWp',
    terminoEstimado: '2025-05-30'
  },
  { 
    projetoInicio: '2024-11-01', 
    contrato: 'BOM012-24', 
    cliente: 'Shopping C', 
    terceirizado: 'Empresa E', 
    localizacao: 'Fortaleza, CE',
    value: 1200000,
    status: 'Suspenso',
    progress: 5,
    prazoContratual: '90 dias',
    ordemServico: 'OS-3011',
    potencia: '75 kWp',
    terminoEstimado: '2025-02-28'
  }
];

export const activities: ActivityRecord[] = Array.from({ length: 8 }, (_, i) => ({
  id: i,
  fase: ['Planejamento', 'Civil', 'Estrutura', 'Elétrica', 'Montagem', 'Comissionamento'][i % 6],
  atividade: `Etapa Técnica ${i + 1}`,
  critico: i % 3 === 0 ? 'Sim' : '',
  inicio: `2024-09-${10 + i}`,
  termino: `2024-09-${15 + i}`,
  conclusao: i < 3 ? 100 : (i === 3 ? 50 : 0),
  cliente: 'Escola A',
  projeto: 'Projeto Escola',
  responsavel: 'Eng. Carlos',
  contrato: 'BOM010-24'
}));

export const financials: FinancialRecord[] = [
  {
    data: '2024-09-01', contrato: 'BOM010-24', projeto: 'Escola A', cliente: 'Escola A', terceirizado: 'Empresa C', localizacao: 'Recife',
    cockpit: 'Contrato', marco: 'Entrada', categoria: 'Equipamentos',
    servicoContratado: 10000, materialContratado: 150000, servicoRealizado: 10000, materialRealizado: 150000, multa: 0, justificativas: ''
  },
  {
    data: '2024-09-15', contrato: 'BOM010-24', projeto: 'Escola A', cliente: 'Escola A', terceirizado: 'Empresa C', localizacao: 'Recife',
    cockpit: 'Terceirizado', marco: 'Medição 1', categoria: 'Civil',
    servicoContratado: 50000, materialContratado: 20000, servicoRealizado: 25000, materialRealizado: 10000, multa: 0, justificativas: ''
  },
  {
    data: '2024-10-01', contrato: 'BOM010-24', projeto: 'Escola A', cliente: 'Escola A', terceirizado: 'Empresa C', localizacao: 'Recife',
    cockpit: 'Operação', marco: 'Manutenção', categoria: 'O&M',
    servicoContratado: 5000, materialContratado: 0, servicoRealizado: 0, materialRealizado: 0, multa: 0, justificativas: ''
  }
];

export const constructionRecords: ConstructionRecord[] = [
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Civil', previsto: 1.0, realizado: 1.0, comentario: 'Concluído' },
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Estrutura Metálica', previsto: 0.8, realizado: 0.8, comentario: 'Avançado' },
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Módulo Solar', previsto: 0.6, realizado: 0.4, comentario: 'Atraso na entrega' },
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Elétrica CC', previsto: 0.4, realizado: 0.2, comentario: '' },
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Inversor', previsto: 0.2, realizado: 0.0, comentario: '' },
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Elétrica CA', previsto: 0.1, realizado: 0.0, comentario: '' },
  { data: '2024-10-01', contrato: 'BOM010-24', categoria: 'Homologação', previsto: 0.0, realizado: 0.0, comentario: '' },
];

export const omRecords: OMRecord[] = Array.from({ length: 12 }, (_, i) => ({
  data: `2024-${String(i + 1).padStart(2, '0')}-01`,
  geracaoPrevista: 10000 + (i * 100) + (Math.random() * 500),
  energiaInjetada: i < 9 ? 9500 + (i * 120) + (Math.random() * 800) : 0,
  kwhCompensado: i < 9 ? 8000 + (i * 100) : 0,
  kwhAcumulado: i < 9 ? 1500 * (i + 1) : 0,
  valorFaturado: i < 9 ? 1200 + (i * 50) : 0,
  gestao: -100,
  fatLiquido: i < 9 ? 1100 + (i * 50) : 0,
  contrato: 'BOM010-24'
}));
