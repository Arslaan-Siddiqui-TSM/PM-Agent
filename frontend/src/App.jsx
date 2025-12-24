import "./App.css";
import { WORKFLOW_STEPS } from "./constants";
import { useProjectWorkflow } from "./hooks";
import { Header, Footer } from "./components/layout";
import { ProgressBar } from "./components/ui";
import {
  UploadStep,
  DevelopmentProcessStep,
  FeasibilityStep,
  ReviewStep,
  PlanStep,
} from "./components/steps";
import { useEffect } from "react";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

function App() {
  const {
    step,
    sessionId,
    loading,
    error,
    successMessage,
    feasibilityReport,
    feasibilityFilePath,
    developmentContextJsonPath,
    finalPlan,
    planFilePath,
    diagrams,
    diagramsLoading,
    handleUpload,
    handleDevelopmentProcessSubmit,
    handleCheckFeasibility,
    handleGeneratePlan,
    handleGenerateDiagrams,
    handleReset,
    setError,
    setSuccessMessage,
  } = useProjectWorkflow();

  // Show error toasts
  useEffect(() => {
    if (error) {
      toast.error(error);
      setError(null);
    }
  }, [error, setError]);

  // Show success toasts
  useEffect(() => {
    if (successMessage) {
      toast.success(successMessage);
      setSuccessMessage(null);
    }
  }, [successMessage, setSuccessMessage]);

  return (
    <div className="app">
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />

      <Header />

      <ProgressBar currentStep={step} />

      <main className="main-content">
        {step === WORKFLOW_STEPS.UPLOAD && (
          <UploadStep loading={loading} onUpload={handleUpload} />
        )}

        {step === WORKFLOW_STEPS.DEVELOPMENT_PROCESS && (
          <DevelopmentProcessStep
            onSubmit={handleDevelopmentProcessSubmit}
            onError={setError}
          />
        )}

        {step === WORKFLOW_STEPS.FEASIBILITY && (
          <FeasibilityStep
            loading={loading}
            onCheckFeasibility={handleCheckFeasibility}
          />
        )}

        {step === WORKFLOW_STEPS.REVIEW && (
          <ReviewStep
            loading={loading}
            feasibilityReport={feasibilityReport}
            feasibilityFilePath={feasibilityFilePath}
            developmentContextJsonPath={developmentContextJsonPath}
            onGeneratePlan={handleGeneratePlan}
          />
        )}

        {step === WORKFLOW_STEPS.PLAN && (
          <PlanStep
            finalPlan={finalPlan}
            planFilePath={planFilePath}
            diagrams={diagrams}
            diagramsLoading={diagramsLoading}
            onGenerateDiagrams={handleGenerateDiagrams}
            onReset={handleReset}
          />
        )}
      </main>

      <Footer sessionId={sessionId} />
    </div>
  );
}

export default App;
