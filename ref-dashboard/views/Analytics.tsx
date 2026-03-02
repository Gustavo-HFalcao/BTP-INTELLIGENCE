
import React from 'react';
import { 
  Radar, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { BarChart3, Target, Zap, TrendingUp, ShieldCheck, AlertTriangle } from 'lucide-react';

const Analytics: React.FC = () => {
  const radarData = [
    { subject: 'Financeiro', A: 85, B: 70, fullMark: 100 },
    { subject: 'Prazo', A: 70, B: 65, fullMark: 100 },
    { subject: 'Qualidade', A: 95, B: 80, fullMark: 100 },
    { subject: 'Segurança', A: 100, B: 90, fullMark: 100 },
    { subject: 'Sustentabilidade', A: 90, B: 60, fullMark: 100 },
    { subject: 'Inovação', A: 80, B: 50, fullMark: 100 },
  ];

  const benchmarkData = [
    { metric: 'Custo/kWp', bomtempo: 3200, market: 3500 },
    { metric: 'Prazo Médio (Dias)', bomtempo: 45, market: 60 },
    { metric: 'Performance Ratio', bomtempo: 82, market: 78 }
  ];

  return (
    <div className="space-y-8 animate-enter">
      <div className="flex flex-col">
        <h2 className="text-3xl font-tech font-bold text-white uppercase">Analytics & Benchmarking</h2>
        <p className="text-[#889999] text-sm">Análise Comparativa e Indicadores de Maturidade</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Eficiência de Capéx', value: '94%', icon: TrendingUp },
          { label: 'OEE Global', value: '88.2%', icon: Zap },
          { label: 'SLA Cumprimento', value: '98%', icon: ShieldCheck },
          { label: 'Taxa de Retrabalho', value: '1.2%', icon: AlertTriangle, isNegative: true }
        ].map((stat, i) => (
          <div key={i} className="glass-panel p-6 rounded-2xl flex items-center space-x-4">
             <div className="p-3 bg-[#ffffff05] rounded-xl text-[#C98B2A] border border-[#ffffff0a]">
               <stat.icon size={20} />
             </div>
             <div>
               <p className="text-[10px] text-[#889999] uppercase font-black">{stat.label}</p>
               <p className="text-xl font-bold text-white font-mono">{stat.value}</p>
             </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Radar Chart */}
        <div className="glass-panel p-8 rounded-3xl">
          <h3 className="text-xl font-tech font-bold text-white mb-6 flex items-center">
            <Target className="mr-3 text-[#C98B2A]" /> Radar de Maturidade
          </h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid stroke="#ffffff10" />
                <PolarAngleAxis dataKey="subject" stroke="#889999" fontSize={12} tick={{ fill: '#889999' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} hide />
                <Radar
                  name="BOMTEMPO"
                  dataKey="A"
                  stroke="#C98B2A"
                  fill="#C98B2A"
                  fillOpacity={0.6}
                />
                <Radar
                  name="Média Mercado"
                  dataKey="B"
                  stroke="#2A9D8F"
                  fill="#2A9D8F"
                  fillOpacity={0.3}
                />
                <Legend />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#081210', border: '1px solid #ffffff10' }}
                  itemStyle={{ color: '#E0E0E0' }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Benchmarking Bar Chart */}
        <div className="glass-panel p-8 rounded-3xl">
          <h3 className="text-xl font-tech font-bold text-white mb-6 flex items-center">
            <BarChart3 className="mr-3 text-[#C98B2A]" /> Benchmarking de Mercado
          </h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={benchmarkData} layout="vertical" barGap={2} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" horizontal={false} />
                <XAxis type="number" stroke="#889999" fontSize={10} hide />
                <YAxis dataKey="metric" type="category" stroke="#E0E0E0" fontSize={12} width={100} />
                <Tooltip cursor={{fill: '#ffffff05'}} contentStyle={{ backgroundColor: '#081210', borderColor: '#ffffff10' }} />
                <Legend />
                <Bar dataKey="bomtempo" name="BOMTEMPO" fill="#C98B2A" radius={[0, 4, 4, 0]} />
                <Bar dataKey="market" name="Mercado" fill="#2A9D8F" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
