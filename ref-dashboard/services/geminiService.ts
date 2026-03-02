
import { GoogleGenAI } from "@google/genai";

export const getGeminiInsight = async (query: string, dataContext: any) => {
  /* Creating a new GoogleGenAI instance with process.env.API_KEY directly as per SDK requirements */
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  
  const systemInstruction = `
    Você é o Assistente Executivo C-Level da BOMTEMPO ENGENHARIA. 
    Seu objetivo é analisar dados de portfolio de engenharia elétrica e fornecer insights estratégicos.
    Aja com profissionalismo, use termos técnicos quando apropriado, mas mantenha a clareza para tomadores de decisão.
    Baseie suas respostas nos dados fornecidos do portfolio.
  `;

  try {
    /* Using generateContent with the recommended contents structure and direct .text property access */
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: {
        parts: [
          { text: `Dados do Portfolio: ${JSON.stringify(dataContext)}` },
          { text: `Pergunta do Executivo: ${query}` }
        ]
      },
      config: {
        systemInstruction,
        temperature: 0.7,
        topP: 0.9,
      }
    });

    return response.text;
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Desculpe, tive um problema ao processar sua análise estratégica. Tente novamente em instantes.";
  }
};
