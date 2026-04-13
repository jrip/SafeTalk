import { createContext, useContext, type ReactNode } from "react";
import type { ISafeTalkApiClient } from "./ISafeTalkApiClient";

const SafeTalkApiContext = createContext<ISafeTalkApiClient | null>(null);

export interface IClientProviderProps {
  readonly client: ISafeTalkApiClient;
  readonly children: ReactNode;
}

export function ClientProvider(props: IClientProviderProps) {
  return <SafeTalkApiContext.Provider value={props.client}>{props.children}</SafeTalkApiContext.Provider>;
}

export function useSafeTalkApi(): ISafeTalkApiClient {
  const client = useContext(SafeTalkApiContext);
  if (client === null) {
    throw new Error("SafeTalk API client is not mounted (wrap app in <ClientProvider>).");
  }
  return client;
}
