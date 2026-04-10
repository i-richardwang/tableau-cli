interface AxiosError {
  isAxiosError: true;
  response?: {
    status: number;
    data: any;
  };
  code?: string;
  message: string;
}

export function isAxiosError(error: unknown): error is AxiosError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as Record<string, unknown>).isAxiosError === true
  );
}
