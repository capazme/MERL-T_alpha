import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card';

interface QualityScoringProps {
  scores: {
    accuracy: number;
    utility: number;
    transparency: number;
  };
  onScoreChange: (scores: { accuracy: number; utility: number; transparency: number }) => void;
}

interface ScoreSliderProps {
  label: string;
  description: string;
  value: number;
  onChange: (value: number) => void;
  icon: string;
  color: string;
}

function ScoreSlider({ label, description, value, onChange, icon, color }: ScoreSliderProps) {
  const getScoreLabel = (score: number) => {
    if (score <= 3) return 'Poor';
    if (score <= 5) return 'Fair';
    if (score <= 7) return 'Good';
    if (score <= 9) return 'Excellent';
    return 'Perfect';
  };

  const getScoreColor = (score: number) => {
    if (score <= 3) return 'text-red-400';
    if (score <= 5) return 'text-orange-400';
    if (score <= 7) return 'text-yellow-400';
    if (score <= 9) return 'text-green-400';
    return 'text-emerald-400';
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <div>
            <div className="font-medium text-slate-200">{label}</div>
            <div className="text-sm text-slate-400">{description}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-white">{value}/10</div>
          <div className={`text-sm font-medium ${getScoreColor(value)}`}>
            {getScoreLabel(value)}
          </div>
        </div>
      </div>
      
      <div className="relative">
        <input
          type="range"
          min="1"
          max="10"
          step="1"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer slider"
          style={{
            background: `linear-gradient(to right, ${color} 0%, ${color} ${(value - 1) * 11.11}%, rgb(51 65 85) ${(value - 1) * 11.11}%, rgb(51 65 85) 100%)`
          }}
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>1</span>
          <span>2</span>
          <span>3</span>
          <span>4</span>
          <span>5</span>
          <span>6</span>
          <span>7</span>
          <span>8</span>
          <span>9</span>
          <span>10</span>
        </div>
      </div>
    </div>
  );
}

export function QualityScoring({ scores, onScoreChange }: QualityScoringProps) {
  const updateScore = (dimension: keyof typeof scores) => (value: number) => {
    onScoreChange({
      ...scores,
      [dimension]: value
    });
  };

  const averageScore = (scores.accuracy + scores.utility + scores.transparency) / 3;
  const getOverallColor = (score: number) => {
    if (score <= 3) return 'text-red-400';
    if (score <= 5) return 'text-orange-400';
    if (score <= 7) return 'text-yellow-400';
    if (score <= 9) return 'text-green-400';
    return 'text-emerald-400';
  };

  return (
    <Card className="border-slate-700">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>📊 Quality Assessment</span>
          <div className="text-right">
            <div className="text-sm text-slate-400">Overall Score</div>
            <div className={`text-lg font-bold ${getOverallColor(averageScore)}`}>
              {averageScore.toFixed(1)}/10
            </div>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <ScoreSlider
          label="Accuracy"
          description="How factually correct is the AI response?"
          value={scores.accuracy}
          onChange={updateScore('accuracy')}
          icon="🎯"
          color="#3b82f6"
        />
        
        <ScoreSlider
          label="Utility"
          description="How useful and practical is this response?"
          value={scores.utility}
          onChange={updateScore('utility')}
          icon="⚡"
          color="#8b5cf6"
        />
        
        <ScoreSlider
          label="Transparency"
          description="How clear and well-reasoned is the explanation?"
          value={scores.transparency}
          onChange={updateScore('transparency')}
          icon="🔍"
          color="#06b6d4"
        />

        <div className="pt-4 border-t border-slate-700">
          <div className="text-sm text-slate-400 mb-2">Score Distribution</div>
          <div className="flex gap-1">
            <div 
              className="h-2 bg-blue-500 rounded-l"
              style={{ width: `${(scores.accuracy / 30) * 100}%` }}
              title={`Accuracy: ${scores.accuracy}/10`}
            />
            <div 
              className="h-2 bg-purple-500"
              style={{ width: `${(scores.utility / 30) * 100}%` }}
              title={`Utility: ${scores.utility}/10`}
            />
            <div 
              className="h-2 bg-cyan-500 rounded-r"
              style={{ width: `${(scores.transparency / 30) * 100}%` }}
              title={`Transparency: ${scores.transparency}/10`}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}