import React from 'react';

interface EvaluationProgressProps {
  currentStep: number;
  totalSteps: number;
  isDevilsAdvocate?: boolean;
}

interface StepInfo {
  number: number;
  title: string;
  description: string;
  icon: string;
}

export function EvaluationProgress({ currentStep, totalSteps, isDevilsAdvocate = false }: EvaluationProgressProps) {
  const steps: StepInfo[] = [
    {
      number: 1,
      title: 'Review',
      description: 'Read task and AI response',
      icon: '👀'
    },
    {
      number: 2,
      title: 'Evaluate',
      description: 'Provide your assessment',
      icon: '📝'
    },
    {
      number: 3,
      title: 'Score',
      description: 'Rate quality dimensions',
      icon: '📊'
    }
  ];

  if (isDevilsAdvocate) {
    steps.push({
      number: 4,
      title: 'Critique',
      description: 'Devil\'s advocate analysis',
      icon: '😈'
    });
  }

  steps.push({
    number: isDevilsAdvocate ? 5 : 4,
    title: 'Confirm',
    description: 'Review and submit',
    icon: '✅'
  });

  const getStepStatus = (stepNumber: number) => {
    if (stepNumber < currentStep) return 'completed';
    if (stepNumber === currentStep) return 'current';
    return 'upcoming';
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500 text-white border-green-500';
      case 'current':
        return 'bg-blue-500 text-white border-blue-500 ring-4 ring-blue-500/30';
      default:
        return 'bg-slate-700 text-slate-400 border-slate-600';
    }
  };

  const getConnectorColor = (stepNumber: number) => {
    return stepNumber < currentStep ? 'bg-green-500' : 'bg-slate-600';
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between relative">
        {/* Progress line */}
        <div className="absolute top-6 left-6 right-6 h-0.5 bg-slate-600 -z-10">
          <div 
            className="h-full bg-green-500 transition-all duration-500 ease-out"
            style={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
          />
        </div>

        {steps.slice(0, totalSteps).map((step, index) => {
          const status = getStepStatus(step.number);
          const isLast = index === steps.slice(0, totalSteps).length - 1;
          
          return (
            <div key={step.number} className="flex flex-col items-center relative">
              {/* Step circle */}
              <div className={`
                w-12 h-12 rounded-full border-2 flex items-center justify-center
                transition-all duration-300 ease-out
                ${getStepColor(status)}
              `}>
                {status === 'completed' ? (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="text-lg">{step.icon}</span>
                )}
              </div>
              
              {/* Step info */}
              <div className="mt-3 text-center min-w-0">
                <div className={`
                  text-sm font-medium
                  ${status === 'current' ? 'text-blue-400' : 
                    status === 'completed' ? 'text-green-400' : 'text-slate-400'}
                `}>
                  {step.title}
                </div>
                <div className="text-xs text-slate-500 mt-1 max-w-20">
                  {step.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current step info */}
      <div className="mt-6 text-center">
        <div className="text-slate-400 text-sm">
          Step {currentStep} of {totalSteps}
        </div>
        <div className="text-white text-lg font-medium mt-1">
          {steps.find(s => s.number === currentStep)?.title}
        </div>
        <div className="text-slate-300 text-sm mt-1">
          {steps.find(s => s.number === currentStep)?.description}
        </div>
      </div>
    </div>
  );
}