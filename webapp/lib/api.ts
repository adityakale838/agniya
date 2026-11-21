// API Service for AGNIYA Backend Integration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export interface UploadResponse {
  success: boolean;
  filename: string;
  records: number;
  fields: number;
  schema: Array<{
    name: string;
    type: string;
    encryption: string;
  }>;
  size_kb: number;
  sample_data?: Record<string, unknown>[];
}

export interface EncryptResponse {
  success: boolean;
  message?: string;
  records_encrypted?: number;
  time_seconds?: number;
  throughput?: number;
  ciphertexts?: number;
}

export interface QueryResponse {
  success: boolean;
  operation: string;
  column: string;
  result: number;
  query_time_ms: number;
  records_processed: number;
  filter_applied?: boolean;
  range?: {
    min: number;
    max: number;
  };
  records_before_filter?: number;
  filter_selectivity?: number;
  security_note?: string;
  query_plan?: {
    strategy: string;
    estimated_cost_ms: number | null;
    actual_cost_ms: number;
    estimated_rows: number | null;
  };
  encryption_proof?: {
    ciphertext_samples: string[];
    ciphertext_bit_lengths: number[];
    modulus_n_bit_length: number;
    verification: string;
    computation_type: string;
    encrypted_result_preview?: string;
    encrypted_result_bit_length?: number;
    note?: string;
    dataset_uniqueness?: string;
    execution_strategy?: string;
  };
}

export interface BenchmarkResponse {
  speedup: number;
  encryption_time_ms: number;
  throughput_rec_per_sec: number;
  operations: Array<{
    name: string;
    hybrid_ms: number;
    paillier_ms: number | null;
  }>;
}

class APIService {
  private async fetchAPI<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'API request failed');
      }

      return response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  async healthCheck(): Promise<{ 
    status: string; 
    message: string; 
    version: string;
    features: {
      paillier_2048: boolean;
      multi_level_cache: boolean;
      batch_packing: boolean;
      precomputation: boolean;
      gpu_acceleration: boolean;
      adaptive_caching: boolean;
      hot_cold_separation: boolean;
      rns_compression?: boolean;
      ciphertext_deduplication?: boolean;
      adaptive_query_planning?: boolean;
    };
    optimizations: {
      precomputation_speedup: string;
      multi_level_cache_speedup: string;
      batch_packing_speedup: string;
      combined_speedup: string;
      rns_compression_ratio?: string;
      bandwidth_reduction?: string;
      dedup_capability?: string;
      query_planning?: string;
    };
  }> {
    return this.fetchAPI('/api/health');
  }

  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Upload failed');
    }

    return response.json();
  }

  async encryptDataset(
    filename: string,
    schema: Array<{ name: string; encryption: string }>,
    sampleSize?: number,
    enableCache: boolean = true,
    enableBatch: boolean = true,
    enableCompression: boolean = true,
    enableDedup: boolean = true
  ): Promise<EncryptResponse> {
    return this.fetchAPI('/api/encrypt', {
      method: 'POST',
      body: JSON.stringify({ 
        filename, 
        schema, 
        sample_size: sampleSize,
        enable_cache: enableCache,
        enable_batch: enableBatch,
        enable_compression: enableCompression,
        enable_dedup: enableDedup
      }),
    });
  }

  async executeQuery(
    operation: string,
    field: string,
    filename: string,
    rangeMin?: number,
    rangeMax?: number
  ): Promise<QueryResponse> {
    const body: Record<string, unknown> = { 
      type: operation,
      column: field, 
      filename 
    };
    
    // Add range parameters if provided
    if (rangeMin !== undefined && rangeMin !== null) {
      body.rangeMin = rangeMin;
    }
    if (rangeMax !== undefined && rangeMax !== null) {
      body.rangeMax = rangeMax;
    }
    
    return this.fetchAPI('/api/query', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async getBenchmarks(): Promise<BenchmarkResponse> {
    return this.fetchAPI('/api/benchmark');
  }
}

export const apiService = new APIService();
