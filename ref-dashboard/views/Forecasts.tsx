
import React from 'react';
import { BrainCircuit, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';

const Forecasts: React.FC = () => {
  return (
    <div className="space-y-8 page-transition">
      <header className="relative bg-gradient-to-r from-[#1A3A30] to-[#0A1F1A] p-12 rounded-3xl border border-[#C98B2A]/30 overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-4">
             <div className="p-2 bg-[#C98B2A] rounded-lg text-[#0A1F1A]">
               <BrainCircuit size={24} />
             </div>
             <h1 className="text-4xl font-black text-white">Previsões Rainforest ML</h1>
          </div>
          <p className="text-[#A0A0A0] max-w-xl">
            Utilizando algoritmos de Random Forest treinados com o histórico da BOMTEMPO para prever atrasos e desvios financeiros antes que ocorram.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-[#0D2A23] p-8 rounded-3xl border border-[#1A3A30]">
          <h3 className="text-xl font-black text-white mb-6">Probabilidade de Atraso (Próximos 30 dias)</h3>
          <div className="space-y-6">
            {[
              { project: 'BOM010-24 (Escola A)', prob: 15, status: 'Baixo Risco' },
              { project: 'BOM011-24 (Hospital B)', prob: 68, status: 'Risco Elevado' },
              { project: 'BOM012-24 (Shopping C)', prob: 42, status: 'Moderado' }
            ].map((p, i) => (
              <div key={i}>
                <div className="flex justify-between items-center mb-2">
                   <span className="text-white font-bold">{p.project}</span>
                   <span className={`text-xs font-black uppercase ${p.prob > 60 ? 'text-red-400' : p.prob > 30 ? 'text-yellow-400' : 'text-green-400'}`}>{p.status}</span>
                </div>
                <div className="h-2 bg-[#0A1F1A] rounded-full overflow-hidden">
                  <div className={`h-full ${p.prob > 60 ? 'bg-red-500' : p.prob > 30 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${p.prob}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#0D2A23] p-8 rounded-3xl border border-[#1A3A30] flex flex-col justify-center text-center">
           <TrendingUp size={48} className="text-[#C98B2A] mx-auto mb-4" />
           <h3 className="text-2xl font-black text-white">Previsão de Margem Final</h3>
           <p className="text-[#A0A0A0] mb-6">O modelo Rainforest estima uma margem consolidada de 18.5% para o Q4.</p>
           <div className="inline-block px-6 py-2 bg-[#C98B2A] text-[#0A1F1A] font-black rounded-full mx-auto">
             CONFIANÇA DO MODELO: 92%
           </div>
        </div>
      </div>
    </div>
  );
};

export default Forecasts;
