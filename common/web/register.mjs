// node --import <this file> --test ...   (see node-hooks.mjs)
import { register } from 'node:module';

register('./node-hooks.mjs', import.meta.url);
