
import React, { useState } from 'react';
import { Zap, Calendar, ArrowDownCircle } from 'lucide-react';
import { omRecords } from '../data/mockData';
import KPICard from '../components/KPICard';
import { ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

const OM: React.FC = () => {
  const [timeFilter, setTimeFilter] = useState<'Mês' | 'Trimestre' | 'Ano'>('Mês');
  
  // Logic to aggregate data based on filter would go here
  // For Mock, we use the monthly records directly
  const data = omRecords;
  const latest = data[data.length - 1] || data[0];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#081210] border border-[#C98B2A]/30 p-3 rounded-lg shadow-xl backdrop-blur-md">
          <p className="text-[#889999] text-[10px] uppercase font-bold mb-1">{label}</p>
          {payload.map((p: any, i: number) => (
             <p key={i} style={{ color: p.color }} className="text-xs font-mono font-bold">
               {p.name}: {p.value.toLocaleString()}
             </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8 animate-enter">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-tech font-bold text-white uppercase">O&M - Gestão de Ativos</h2>
          <p className="text-[#889999] text-sm">Performance Energética e Resultados</p>
        </div>
        
        <div className="flex bg-[#ffffff05] p-1 rounded-xl border border-[#ffffff0a]">
          {['Mês', 'Trimestre', 'Ano'].map((t) => (
            <button
              key={t}
              onClick={() => setTimeFilter(t as any)}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                timeFilter === t ? 'bg-[#C98B2A] text-[#030504]' : 'text-[#889999] hover:text-white'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <KPICard label="Energia Injetada (Mês)" value={`${(latest.energiaInjetada).toLocaleString()} kWh`} icon={Zap} />
        <KPICard label="Acumulado (Ano)" value={`${(latest.kwhAcumulado).toLocaleString()} kWh`} icon={Zap} delta="Total" />
        <KPICard label="Performance" value={`${((latest.energiaInjetada/latest.geracaoPrevista)*100).toFixed(1)}%`} icon={ArrowDownCircle} isPositive={true} />
        <KPICard label="Fat. Líquido" value={`R$ ${latest.fatLiquido.toFixed(2)}`} icon={Calendar} />
      </div>

      {/* Composed Chart: Accumulated (Bar) vs Predicted/Injected (Line) */}
      <div className="glass-panel p-8 rounded-3xl">
        <h3 className="text-white font-tech text-xl font-bold mb-6">Performance de Geração</h3>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
              <XAxis dataKey="data" stroke="#889999" fontSize={10} tickFormatter={(val) => val.substring(5,7)} />
              <YAxis yAxisId="left" stroke="#889999" fontSize={10} />
              <YAxis yAxisId="right" orientation="right" stroke="#889999" fontSize={10} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              
              <Bar yAxisId="right" dataKey="kwhAcumulado" name="kWh Acumulado" fill="#ffffff10" radius={[4, 4, 0, 0]} barSize={20} />
              <Line yAxisId="left" type="monotone" dataKey="geracaoPrevista" name="Previsto" stroke="#E0A63B" strokeDasharray="5 5" dot={false} strokeWidth={2} />
              <Line yAxisId="left" type="monotone" dataKey="energiaInjetada" name="Injetado" stroke="#2A9D8F" strokeWidth={3} dot={{r: 4, fill:'#030504', strokeWidth: 2}} activeDot={{r: 6}} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Table */}
      <div className="glass-panel rounded-3xl overflow-hidden">
         <div className="overflow-x-auto">
           <table className="w-full text-left">
             <thead className="bg-[#ffffff03]">
               <tr>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase">Data</th>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase text-right">Injetada (kWh)</th>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase text-right">Compensada (kWh)</th>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase text-right">Acumulada (kWh)</th>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase text-right">Valor Faturado</th>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase text-right">Gestão</th>
                 <th className="p-4 text-[10px] font-black text-[#889999] uppercase text-right">Fat. Líquido</th>
               </tr>
             </thead>
             <tbody className="divide-y divide-[#ffffff0a]">
               {data.map((row, i) => (
                 <tr key={i} className="hover:bg-[#ffffff03] transition-colors">
                   <td className="p-4 text-white font-mono text-xs">{row.data}</td>
                   <td className="p-4 text-[#2A9D8F] font-mono text-xs text-right font-bold">{row.energiaInjetada.toLocaleString()}</td>
                   <td className="p-4 text-[#889999] font-mono text-xs text-right">{row.kwhCompensado.toLocaleString()}</td>
                   <td className="p-4 text-white font-mono text-xs text-right">{row.kwhAcumulado.toLocaleString()}</td>
                   <td className="p-4 text-white font-mono text-xs text-right">R$ {row.valorFaturado.toFixed(2)}</td>
                   <td className="p-4 text-[#EF4444] font-mono text-xs text-right">R$ {row.gestao.toFixed(2)}</td>
                   <td className="p-4 text-[#C98B2A] font-mono text-xs text-right font-bold">R$ {row.fatLiquido.toFixed(2)}</td>
                 </tr>
               ))}
             </tbody>
           </table>
         </div>
      </div>
    </div>
  );
};

export default OM;
