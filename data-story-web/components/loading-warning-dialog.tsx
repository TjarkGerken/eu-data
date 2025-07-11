"use client";

import { useState, useEffect } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useLanguage } from "@/contexts/language-context";
import { Checkbox } from "@/components/ui/checkbox";

interface LoadingWarningDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

const STORAGE_KEY = "hideLoadingWarning";

export function LoadingWarningDialog({
  isOpen,
  onClose,
}: LoadingWarningDialogProps) {
  const { t } = useLanguage();
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleClose = () => {
    if (dontShowAgain) {
      localStorage.setItem(STORAGE_KEY, "true");
    }
    onClose();
  };

  const handleUnderstand = () => {
    handleClose();
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={onClose}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-lg font-semibold text-[#2d5a3d]">
            {t.loadingWarningTitle}
          </AlertDialogTitle>
          <AlertDialogDescription className="text-sm text-muted-foreground leading-relaxed">
            {t.loadingWarningMessage}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex items-center space-x-2 py-2">
          <Checkbox
            id="dontShowAgain"
            checked={dontShowAgain}
            onCheckedChange={(checked) => setDontShowAgain(checked === true)}
          />
          <label
            htmlFor="dontShowAgain"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            {t.loadingWarningDontShowAgain}
          </label>
        </div>

        <AlertDialogFooter>
          <AlertDialogAction onClick={handleUnderstand}>
            {t.loadingWarningUnderstand}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// Hook to check if warning should be shown
export function useLoadingWarning() {
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    // Only check on client side to avoid hydration issues
    const hideWarning = localStorage.getItem(STORAGE_KEY);
    setShouldShow(!hideWarning);
  }, []);

  return shouldShow;
}
