// API Service for AGNIYA Backend Integration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

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
}

export interface EncryptResponse {
  success: boolean;
  records_encrypted: number;
  total_records: number;
  original_dataset_size: number;
  sampled: boolean;
  time_seconds: number;
  cache_time_seconds: number;
  encrypt_time_seconds: number;
  throughput: number;
  speedup: number;
  optimizations_used: {
    multi_level_cache: boolean;
    batch_packing: boolean;
    precomputation: boolean;
    cache_size: number;
  };
  cache_stats: {
    hits: number;
    misses: number;
    hit_rate: number;
  };
  paillier_fields: string[];
  database_id: string;
}

export interface QueryResponse {
  success: boolean;
  operation: string;
  field: string;
  result: number;
  time_ms: number;
  records_processed: number;
  encrypted_computation: boolean;
  optimizations_used: {
    batch_packing: boolean;
    multi_level_cache: boolean;
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
    };
    optimizations: {
      precomputation_speedup: string;
      multi_level_cache_speedup: string;
      batch_packing_speedup: string;
      combined_speedup: string;
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
    enableBatch: boolean = true
  ): Promise<EncryptResponse> {
    return this.fetchAPI('/api/encrypt', {
      method: 'POST',
      body: JSON.stringify({ 
        filename, 
        schema, 
        sample_size: sampleSize,
        enable_cache: enableCache,
        enable_batch: enableBatch
      }),
    });
  }

  async executeQuery(
    operation: string,
    field: string,
    filename: string
  ): Promise<QueryResponse> {
    return this.fetchAPI('/api/query', {
      method: 'POST',
      body: JSON.stringify({ operation, field, filename }),
    });
  }

  async getBenchmarks(): Promise<BenchmarkResponse> {
    return this.fetchAPI('/api/benchmark');
  }
}

export const apiService = new APIService();
