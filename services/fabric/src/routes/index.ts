/**
 * STIX Fabric API routes.
 */

import type { FastifyInstance, FastifyReply } from 'fastify';
import { z } from 'zod';
import type {
  FabricAgent,
  FabricEnforcementPoint,
  FabricGraphSummary,
  FabricPolicyChannel,
  FabricRegistryStats,
  FabricToolAction,
} from '@stix/fabric-types';
import type { FabricStore } from '../store/index.js';

interface FabricRouteOptions {
  store: FabricStore;
}

const environmentSchema = z.enum(['dev', 'test', 'stage', 'prod']);
const riskTierSchema = z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
const statusSchema = z.enum(['ACTIVE', 'INACTIVE', 'QUARANTINED', 'DECOMMISSIONED']);
const metadataSchema = z.record(z.unknown()).default({});

const createAgentSchema = z.object({
  agent_id: z.string().min(1).optional(),
  display_name: z.string().min(1),
  owner: z.string().min(1),
  runtime: z.string().min(1),
  environment: environmentSchema,
  risk_tier: riskTierSchema,
  status: statusSchema.default('ACTIVE'),
  labels: z.array(z.string()).default([]),
  metadata: metadataSchema,
});

const createEnforcementPointSchema = z.object({
  enforcement_point_id: z.string().min(1).optional(),
  display_name: z.string().min(1),
  type: z.enum(['sdk', 'ci', 'mcp_gateway', 'tool_gateway', 'service_gateway', 'target']),
  environment: environmentSchema,
  status: statusSchema.default('ACTIVE'),
  url: z.string().url().optional(),
  agent_ids: z.array(z.string()).default([]),
  metadata: metadataSchema,
});

const createToolActionSchema = z.object({
  action_id: z.string().min(1).optional(),
  display_name: z.string().min(1),
  action: z.string().min(1),
  resource_type: z.string().min(1),
  risk_tier: riskTierSchema,
  approval_required: z.boolean().default(false),
  allowed_environments: z.array(environmentSchema).min(1),
  metadata: metadataSchema,
});

const createPolicyChannelSchema = z.object({
  channel_id: z.string().min(1).optional(),
  display_name: z.string().min(1),
  environment: environmentSchema,
  rollout_state: z.enum(['DRAFT', 'CANARY', 'ACTIVE', 'PAUSED', 'RETIRED']).default('DRAFT'),
  active_bundle_id: z.string().min(1).optional(),
  metadata: metadataSchema,
});

export async function fabricRoutes(
  fastify: FastifyInstance,
  options: FabricRouteOptions
): Promise<void> {
  const { store } = options;

  fastify.get('/api/v1/fabric/agents', async (_request, reply) => {
    const data = await store.listAgents();
    return reply.code(200).send(collection(data));
  });

  fastify.post('/api/v1/fabric/agents', async (request, reply) => {
    const input = parseBody(createAgentSchema, request.body, reply);
    if (!input) return;
    const data = await store.createAgent(input);
    return reply.code(201).send(data);
  });

  fastify.get<{ Params: { agentId: string } }>('/api/v1/fabric/agents/:agentId', async (request, reply) => {
    const data = await store.getAgent(request.params.agentId);
    if (!data) return notFound(reply, 'AGENT_NOT_FOUND', request.params.agentId);
    return reply.code(200).send(data);
  });

  fastify.get('/api/v1/fabric/enforcement-points', async (_request, reply) => {
    const data = await store.listEnforcementPoints();
    return reply.code(200).send(collection(data));
  });

  fastify.post('/api/v1/fabric/enforcement-points', async (request, reply) => {
    const input = parseBody(createEnforcementPointSchema, request.body, reply);
    if (!input) return;
    const data = await store.createEnforcementPoint(input);
    return reply.code(201).send(data);
  });

  fastify.get<{ Params: { enforcementPointId: string } }>(
    '/api/v1/fabric/enforcement-points/:enforcementPointId',
    async (request, reply) => {
      const data = await store.getEnforcementPoint(request.params.enforcementPointId);
      if (!data) return notFound(reply, 'ENFORCEMENT_POINT_NOT_FOUND', request.params.enforcementPointId);
      return reply.code(200).send(data);
    }
  );

  fastify.get('/api/v1/fabric/tool-actions', async (_request, reply) => {
    const data = await store.listToolActions();
    return reply.code(200).send(collection(data));
  });

  fastify.post('/api/v1/fabric/tool-actions', async (request, reply) => {
    const input = parseBody(createToolActionSchema, request.body, reply);
    if (!input) return;
    const data = await store.createToolAction(input);
    return reply.code(201).send(data);
  });

  fastify.get<{ Params: { actionId: string } }>('/api/v1/fabric/tool-actions/:actionId', async (request, reply) => {
    const data = await store.getToolAction(request.params.actionId);
    if (!data) return notFound(reply, 'TOOL_ACTION_NOT_FOUND', request.params.actionId);
    return reply.code(200).send(data);
  });

  fastify.get('/api/v1/fabric/policy-channels', async (_request, reply) => {
    const data = await store.listPolicyChannels();
    return reply.code(200).send(collection(data));
  });

  fastify.post('/api/v1/fabric/policy-channels', async (request, reply) => {
    const input = parseBody(createPolicyChannelSchema, request.body, reply);
    if (!input) return;
    const data = await store.createPolicyChannel(input);
    return reply.code(201).send(data);
  });

  fastify.get<{ Params: { channelId: string } }>('/api/v1/fabric/policy-channels/:channelId', async (request, reply) => {
    const data = await store.getPolicyChannel(request.params.channelId);
    if (!data) return notFound(reply, 'POLICY_CHANNEL_NOT_FOUND', request.params.channelId);
    return reply.code(200).send(data);
  });

  fastify.get('/api/v1/fabric/stats', async (_request, reply) => {
    const data = await store.getStats();
    return reply.code(200).send(data);
  });

  fastify.get('/api/v1/fabric/graph/summary', async (_request, reply) => {
    const data = await store.getGraphSummary();
    return reply.code(200).send(data);
  });
}

export async function healthRoutes(
  fastify: FastifyInstance,
  options: FabricRouteOptions & { startTime: number; version: string }
): Promise<void> {
  const { store, startTime, version } = options;

  fastify.get('/health', async (_request, reply) => {
    return reply.code(200).send({
      status: 'healthy',
      service: 'stix-fabric',
      version,
      uptime: Math.floor((Date.now() - startTime) / 1000),
      timestamp: new Date().toISOString(),
    });
  });

  fastify.get('/ready', async (_request, reply) => {
    const storeHealthy = await store.health();
    return reply.code(storeHealthy ? 200 : 503).send({
      ready: storeHealthy,
      status: storeHealthy ? 'healthy' : 'unhealthy',
      service: 'stix-fabric',
      version,
      checks: {
        store: { status: storeHealthy ? 'pass' : 'fail' },
      },
    });
  });
}

function collection<T>(data: T[]): { data: T[]; total: number } {
  return { data, total: data.length };
}

function parseBody<T extends z.ZodTypeAny>(
  schema: T,
  body: unknown,
  reply: FastifyReply
): z.infer<T> | null {
  const parsed = schema.safeParse(body);
  if (parsed.success) {
    return parsed.data;
  }

  reply.code(400).send({
    error: 'Validation failed',
    details: parsed.error.issues.map((issue) => ({
      path: issue.path.join('.'),
      message: issue.message,
    })),
  });
  return null;
}

function notFound(reply: FastifyReply, code: string, id: string): FastifyReply {
  return reply.code(404).send({
    success: false,
    error: {
      code,
      message: `Fabric registry record not found: ${id}`,
    },
  });
}

export type {
  FabricAgent,
  FabricEnforcementPoint,
  FabricToolAction,
  FabricPolicyChannel,
  FabricRegistryStats,
  FabricGraphSummary,
};
