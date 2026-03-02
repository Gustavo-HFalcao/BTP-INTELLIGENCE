
import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';
import { Wallet, DollarSign, Filter, TrendingUp } from 'lucide-react';
import { financials, contracts } from '../data/mockData';
import KPICard from '../components/KPICard';

const Finance: React.FC = () => {
  const [selectedCockpit, setSelectedCockpit] = useState<string>('Todos');

  const filteredData = selectedCockpit === 'Todos' 
    ? financials 
    : financials.filter(f => f.cockpit === selectedCockpit);

  const totalContratado = filteredData.reduce((acc, curr) => acc + curr.servicoContratado + curr.materialContratado, 0);
  const totalMedido = filteredData.reduce((acc, curr) => acc + curr.servicoRealizado + curr.materialRealizado, 0);
  const aMedir = totalContratado - totalMedido;

  // Chart Data for "Medido vs A Medir"
  const balanceData = [
    { name: 'Medido (Realizado)', value: totalMedido },
    { name: 'A Medir (Saldo)', value: aMedir }
  ];

  // Cost by Area (Cockpit)
  const costByArea = [
    { name: 'Cliente', value: financials.filter(f => f.cockpit === 'Contrato').reduce((acc, curr) => acc + curr.servicoContratado + curr.materialContratado, 0) },
    { name: 'Terceirizado', value: financials.filter(f => f.cockpit === 'Terceirizado').reduce((acc, curr) => acc + curr.servicoContratado + curr.materialContratado, 0) },
    { name: 'Operação', value: financials.filter(f => f.cockpit === 'Operação').reduce((acc, curr) => acc + curr.servicoContratado + curr.materialContratado, 0) }
  ];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#081210] border border-[#C98B2A]/30 p-3 rounded-lg shadow-xl backdrop-blur-md">
          <p className="text-[#889999] text-[10px] uppercase font-bold mb-1">{payload[0].name}</p>
          <p className="text-[#E0E0E0] font-tech font-bold">R$ {payload[0].value.toLocaleString()}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8 animate-enter">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h2 className="text-3xl font-tech font-bold text-white uppercase">Financeiro</h2>
          <p className="text-[#889999] text-sm">Controle de Custos e Medições</p>
        </div>
        <div className="flex items-center gap-2 bg-[#ffffff05] p-2 rounded-xl border border-[#ffffff0a]">
          <Filter size={16} className="text-[#C98B2A] ml-2" />
          <select 
            value={selectedCockpit}
            onChange={(e) => setSelectedCockpit(e.target.value)}
            className="bg-transparent text-white text-sm outline-none px-2 py-1 font-mono"
          >
            <option value="Todos" className="bg-[#030504]">Todos os Cockpits</option>
            <option value="Contrato" className="bg-[#030504]">Cliente</option>
            <option value="Terceirizado" className="bg-[#030504]">Terceirizado</option>
            <option value="Operação" className="bg-[#030504]">Operação</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard label="Total Contratado" value={`R$ ${(totalContratado / 1000).toFixed(1)}k`} icon={Wallet} />
        <KPICard label="Total Medido" value={`R$ ${(totalMedido / 1000).toFixed(1)}k`} icon={DollarSign} delta="Executado" isPositive={true} />
        <KPICard label="Saldo à Medir" value={`R$ ${(aMedir / 1000).toFixed(1)}k`} icon={TrendingUp} delta="Pendente" isPositive={false} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Medido vs A Medir Chart */}
        <div className="glass-panel p-8 rounded-3xl">
          <h3 className="text-white font-tech text-xl font-bold mb-6">Status de Medição Global</h3>
          <div className="h-[300px] w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                 <Pie
                    data={balanceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={80}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                 >
                   <Cell fill="#2A9D8F" /> {/* Medido */}
                   <Cell fill="#ffffff10" stroke="#ffffff20" /> {/* A Medir */}
                 </Pie>
                 <Tooltip content={<CustomTooltip />} />
                 <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cost Breakdown Bar Chart */}
        <div className="glass-panel p-8 rounded-3xl">
          <h3 className="text-white font-tech text-xl font-bold mb-6">Custos por Centro (Cockpit)</h3>
          <div className="h-[300px]">
             <ResponsiveContainer width="100%" height="100%">
               <BarChart data={costByArea} layout="vertical" margin={{ left: 20 }}>
                 <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" horizontal={false} />
                 <XAxis type="number" stroke="#889999" fontSize={10} tickFormatter={(val) => `R$${val/1000}k`} />
                 <YAxis dataKey="name" type="category" stroke="#E0E0E0" fontSize={12} width={80} />
                 <Tooltip cursor={{fill: '#ffffff05'}} content={<CustomTooltip />} />
                 <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    <Cell fill="#C98B2A" />
                    <Cell fill="#E0A63B" />
                    <Cell fill="#2A9D8F" />
                 </Bar>
               </BarChart>
             </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Detailed Table */}
      <div className="glass-panel rounded-3xl overflow-hidden">
        <div className="p-6 border-b border-[#ffffff0a]">
           <h3 className="text-white font-tech text-lg font-bold">Detalhamento Financeiro por Marco</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-[#ffffff03]">
              <tr>
                <th className="p-4 text-[10px] font-black text-[#889999] uppercase tracking-wider">Cockpit</th>
                <th className="p-4 text-[10px] font-black text-[#889999] uppercase tracking-wider">Marco</th>
                <th className="p-4 text-[10px] font-black text-[#889999] uppercase tracking-wider">Categoria</th>
                <th className="p-4 text-[10px] font-black text-[#889999] uppercase tracking-wider text-right">Contratado</th>
                <th className="p-4 text-[10px] font-black text-[#889999] uppercase tracking-wider text-right">Medido</th>
                <th className="p-4 text-[10px] font-black text-[#889999] uppercase tracking-wider text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ffffff0a]">
              {filteredData.map((f, i) => {
                const totalC = f.servicoContratado + f.materialContratado;
                const totalR = f.servicoRealizado + f.materialRealizado;
                const pct = totalC > 0 ? (totalR / totalC) * 100 : 0;
                
                return (
                  <tr key={i} className="hover:bg-[#ffffff03] transition-colors">
                    <td className="p-4 text-white font-bold text-xs">{f.cockpit}</td>
                    <td className="p-4 text-[#C98B2A] font-mono text-xs">{f.marco}</td>
                    <td className="p-4 text-[#889999] text-xs">{f.categoria}</td>
                    <td className="p-4 font-mono text-xs text-right text-white">R$ {totalC.toLocaleString()}</td>
                    <td className="p-4 font-mono text-xs text-right text-[#2A9D8F]">R$ {totalR.toLocaleString()}</td>
                    <td className="p-4">
                      <div className="w-24 h-2 bg-[#ffffff0a] rounded-full mx-auto overflow-hidden">
                        <div className="h-full bg-[#C98B2A]" style={{ width: `${pct}%` }}></div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Finance;
