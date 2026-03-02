
import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Cell,
  PieChart,
  Pie
} from 'recharts';
import { 
  TrendingUp, 
  DollarSign, 
  HardHat, 
  Target, 
  Activity
} from 'lucide-react';
import KPICard from '../components/KPICard';
import { contracts } from '../data/mockData';

const Overview: React.FC = () => {
  const totalValue = contracts.reduce((acc, curr) => acc + curr.value, 0);
  const activeContracts = contracts.filter(c => c.status === 'Em Execução').length;
  const avgProgress = Math.round(contracts.reduce((acc, curr) => acc + curr.progress, 0) / (contracts.length || 1));
  
  const statusData = [
    { name: 'Em Execução', value: activeContracts },
    { name: 'Concluído', value: contracts.filter(c => c.status === 'Concluído').length },
    { name: 'Suspenso', value: contracts.filter(c => c.status === 'Suspenso').length }
  ];

  const chartData = contracts.map(c => ({
    name: c.cliente.split(' ')[0],
    value: c.value / 1000000,
    progress: c.progress
  }));

  // Custom Tooltip for Recharts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#081210] border border-[#C98B2A]/30 p-3 rounded-lg shadow-xl backdrop-blur-md">
          <p className="text-[#889999] text-[10px] uppercase font-bold mb-1">{label}</p>
          <p className="text-[#E0E0E0] font-tech font-bold">R$ {payload[0].value.toFixed(1)}M</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <header className="relative glass-panel p-12 rounded-3xl overflow-hidden animate-enter">
        <div className="absolute inset-0 bg-gradient-to-r from-[#C98B2A]/10 via-transparent to-transparent pointer-events-none"></div>
        <div className="absolute right-0 top-0 p-12 opacity-10 pointer-events-none">
           <Activity size={200} strokeWidth={0.5} />
        </div>
        
        <div className="relative z-10 max-w-2xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="px-2 py-1 bg-[#C98B2A] text-[#030504] text-[10px] font-bold uppercase tracking-widest rounded-sm">
              System Online
            </div>
            <div className="h-[1px] w-12 bg-[#C98B2A]/50"></div>
          </div>
          <h1 className="text-5xl font-bold text-white mb-4 tracking-tight font-tech">VISÃO GERAL</h1>
          <p className="text-[#889999] text-lg font-light">
            Centro de Comando BOMTEMPO. Telemetria financeira, velocidade operacional e marcadores estratégicos em tempo real.
          </p>
        </div>
      </header>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard 
          label="Receita Total" 
          value={`R$ ${(totalValue / 1000000).toFixed(1)}M`} 
          icon={DollarSign} 
          delta="+12.5%" 
          delay={100}
        />
        <KPICard 
          label="Contratos Ativos" 
          value={activeContracts} 
          icon={HardHat} 
          delay={200}
        />
        <KPICard 
          label="Velocidade Média" 
          value={`${avgProgress}%`} 
          icon={TrendingUp} 
          delta="+2.1%"
          delay={300}
        />
        <KPICard 
          label="Health Score" 
          value="94.2" 
          icon={Target} 
          isPositive={true}
          delay={400}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Chart */}
        <div className="lg:col-span-2 glass-panel p-8 rounded-3xl animate-enter delay-300">
          <div className="flex justify-between items-center mb-8">
             <div>
                <h3 className="text-[#E0E0E0] font-tech text-xl font-bold">Alocação de Volume</h3>
                <p className="text-[#889999] text-xs uppercase tracking-widest">Receita por Entidade</p>
             </div>
             <div className="flex gap-2">
                <span className="w-3 h-3 rounded-full bg-[#C98B2A]"></span>
                <span className="w-3 h-3 rounded-full bg-[#2A9D8F]"></span>
             </div>
          </div>
          
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={40}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
                <XAxis 
                  dataKey="name" 
                  stroke="#889999" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false} 
                  tick={{fontFamily: 'JetBrains Mono'}}
                />
                <YAxis 
                  stroke="#889999" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(value) => `R$${value}M`}
                  tick={{fontFamily: 'JetBrains Mono'}}
                />
                <Tooltip cursor={{fill: '#ffffff05'}} content={<CustomTooltip />} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#C98B2A' : '#2A9D8F'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Secondary Chart */}
        <div className="glass-panel p-8 rounded-3xl animate-enter delay-400">
          <div className="mb-8">
            <h3 className="text-[#E0E0E0] font-tech text-xl font-bold">Status do Portfolio</h3>
            <p className="text-[#889999] text-xs uppercase tracking-widest">Distribuição Operacional</p>
          </div>
          
          <div className="h-[250px] relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={8}
                  dataKey="value"
                  stroke="none"
                >
                  <Cell fill="#C98B2A" />
                  <Cell fill="#2A9D8F" />
                  <Cell fill="#E0E0E0" />
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            
            {/* Center Stat */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
               <span className="text-3xl font-tech font-bold text-white">{contracts.length}</span>
               <span className="text-[9px] text-[#889999] uppercase tracking-widest">Total</span>
            </div>
          </div>

          <div className="space-y-3 mt-6">
            {statusData.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-[#ffffff03] border border-[#ffffff05]">
                <div className="flex items-center gap-3">
                   <div className={`w-2 h-2 rounded-sm ${idx === 0 ? 'bg-[#C98B2A]' : idx === 1 ? 'bg-[#2A9D8F]' : 'bg-[#E0E0E0]'}`}></div>
                   <span className="text-[#889999] text-xs font-bold uppercase tracking-wider">{item.name}</span>
                </div>
                <span className="text-white font-mono text-xs">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overview;
