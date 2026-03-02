
import React, { useState } from 'react';
import { constructionRecords, contracts } from '../data/mockData';
import { Filter, Zap, LayoutTemplate } from 'lucide-react';

const Gauge = ({ value }: { value: number }) => {
  const radius = 80;
  const stroke = 12;
  const normalizedValue = Math.min(Math.max(value, 0), 100);
  const circumference = radius * Math.PI;
  const strokeDashoffset = circumference - (normalizedValue / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg height={radius * 2} width={radius * 2} className="rotate-[-180deg]">
        <circle
          stroke="#ffffff0a"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="transparent"
          r={radius - stroke / 2}
          cx={radius}
          cy={radius}
          style={{ strokeDasharray: `${circumference} ${circumference}`, strokeDashoffset: 0 }}
        />
        <circle
          stroke="#C98B2A"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="transparent"
          r={radius - stroke / 2}
          cx={radius}
          cy={radius}
          style={{ 
            strokeDasharray: `${circumference} ${circumference}`, 
            strokeDashoffset,
            transition: 'stroke-dashoffset 1s ease-out'
          }}
        />
      </svg>
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-[20%] text-center">
         <span className="text-4xl font-tech font-bold text-white block">{value}%</span>
         <span className="text-[10px] text-[#889999] uppercase tracking-widest">Conclusão</span>
      </div>
    </div>
  );
};

const Construction: React.FC = () => {
  const [selectedContract, setSelectedContract] = useState(contracts[0].contrato);
  const currentContract = contracts.find(c => c.contrato === selectedContract) || contracts[0];
  const records = constructionRecords.filter(r => r.contrato === selectedContract);

  // Calculate overall progress based on categories (simplified average for mock)
  const overallProgress = Math.round(
    records.reduce((acc, curr) => acc + curr.realizado, 0) / (records.length || 1) * 100
  );

  return (
    <div className="space-y-8 animate-enter">
      {/* Filters */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
           <h2 className="text-3xl font-tech font-bold text-white uppercase">Field Operations</h2>
           <p className="text-[#889999] text-sm">Acompanhamento de Obras em Tempo Real</p>
        </div>
        <div className="flex items-center gap-2 bg-[#ffffff05] p-2 rounded-xl border border-[#ffffff0a]">
          <Filter size={16} className="text-[#C98B2A] ml-2" />
          <select 
            value={selectedContract}
            onChange={(e) => setSelectedContract(e.target.value)}
            className="bg-transparent text-white text-sm outline-none px-2 py-1 font-mono"
          >
            {contracts.map(c => (
              <option key={c.contrato} value={c.contrato} className="bg-[#030504]">
                {c.contrato} - {c.cliente}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Main Indicators Column */}
        <div className="lg:col-span-2 space-y-8">
          {/* Detailed Project Info Block */}
          <div className="glass-panel p-8 rounded-3xl">
            <h3 className="text-[#C98B2A] font-tech text-xl font-bold mb-6 flex items-center">
               <LayoutTemplate className="mr-2" size={20} /> Detalhamento da Obra
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
               <div className="space-y-1">
                 <p className="text-[10px] text-[#889999] uppercase font-bold">Cliente</p>
                 <p className="text-white font-bold">{currentContract.cliente}</p>
               </div>
               <div className="space-y-1">
                 <p className="text-[10px] text-[#889999] uppercase font-bold">Ordem de Serviço</p>
                 <p className="text-white font-mono">{currentContract.ordemServico}</p>
               </div>
               <div className="space-y-1">
                 <p className="text-[10px] text-[#889999] uppercase font-bold">Potência</p>
                 <p className="text-[#C98B2A] font-tech font-bold text-lg">{currentContract.potencia}</p>
               </div>
               <div className="space-y-1">
                 <p className="text-[10px] text-[#889999] uppercase font-bold">Prazo</p>
                 <p className="text-white font-mono">{currentContract.prazoContratual}</p>
               </div>
            </div>
          </div>

          {/* Category Progress Bars */}
          <div className="glass-panel p-8 rounded-3xl">
             <h3 className="text-white font-tech text-xl font-bold mb-6">Progresso por Disciplina</h3>
             <div className="space-y-6">
               {records.map((rec, i) => (
                 <div key={i} className="group">
                   <div className="flex justify-between items-end mb-2">
                      <span className="text-sm font-bold text-white">{rec.categoria}</span>
                      <div className="flex gap-4 text-xs font-mono">
                         <span className="text-[#889999]">P: {(rec.previsto * 100).toFixed(0)}%</span>
                         <span className={`${rec.realizado >= rec.previsto ? 'text-[#2A9D8F]' : 'text-[#EF4444]'}`}>
                           R: {(rec.realizado * 100).toFixed(0)}%
                         </span>
                      </div>
                   </div>
                   <div className="h-2 bg-[#ffffff05] rounded-full overflow-hidden relative">
                      {/* Realizado Bar */}
                      <div 
                        className={`absolute top-0 left-0 h-full rounded-full transition-all duration-1000 ${
                          rec.realizado >= rec.previsto ? 'bg-[#2A9D8F]' : 'bg-[#EF4444]'
                        }`} 
                        style={{ width: `${rec.realizado * 100}%`, zIndex: 2 }}
                      ></div>
                      {/* Previsto Marker (Ghost bar) */}
                      <div 
                        className="absolute top-0 left-0 h-full bg-[#ffffff20] border-r-2 border-white/50" 
                        style={{ width: `${rec.previsto * 100}%`, zIndex: 1 }}
                      ></div>
                   </div>
                   {rec.comentario && (
                     <p className="text-[10px] text-[#889999] mt-1 italic">{rec.comentario}</p>
                   )}
                 </div>
               ))}
             </div>
          </div>
        </div>

        {/* Speedometer & Highlights Column */}
        <div className="space-y-8">
          <div className="glass-panel p-8 rounded-3xl flex flex-col items-center justify-center text-center">
             <h3 className="text-[#889999] text-xs uppercase tracking-widest mb-6 font-bold">Avanço Físico Global</h3>
             <div className="h-[120px] overflow-hidden">
               <Gauge value={overallProgress} />
             </div>
             <p className="mt-4 text-sm text-[#E0E0E0] max-w-[200px]">
               Indicador consolidado ponderado pelo peso financeiro de cada etapa.
             </p>
          </div>

          <div className="glass-panel p-6 rounded-3xl border border-[#2A9D8F]/20">
             <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-[#2A9D8F]/20 text-[#2A9D8F] rounded-lg">
                  <Zap size={20} />
                </div>
                <div>
                   <h4 className="text-white font-bold text-sm">Status Crítico</h4>
                   <p className="text-[10px] text-[#889999] uppercase">Alertas do Sistema</p>
                </div>
             </div>
             <div className="space-y-2">
                <div className="p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-lg text-xs text-[#EF4444]">
                   <strong>Atraso:</strong> Módulo Solar (Impacto: 2 dias)
                </div>
                <div className="p-3 bg-[#C98B2A]/10 border border-[#C98B2A]/20 rounded-lg text-xs text-[#C98B2A]">
                   <strong>Atenção:</strong> Logística Inversor
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Construction;
