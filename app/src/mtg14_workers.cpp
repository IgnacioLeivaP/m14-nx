// Magic 2014 TU: trabajador 82C65F08, cuerpo generado mas pausa tras 64 sondeos vacios.
// Ready byte: *(*(worker+0x40)+0xE13C). Ver work/worker14_disasm.log.
#include "generated/default/mtg14_init.h"
#include <chrono>
#include <thread>
#include <rex/cvar.h>
REXCVAR_DEFINE_INT32(mtg14_worker_idle_us, 100, "Mtg14", "Sleep after 64 empty worker polls; 0 disables")
    .range(0, 5000);
extern "C" REX_FUNC(sub_82C65F08) {
	REX_FUNC_PROLOGUE();
    uint32_t idle_polls = 0;
    const int idle_us = REXCVAR_GET(mtg14_worker_idle_us);
	PPCRegister ctr{};
	PPCXERRegister xer{};
	PPCRegister reserved{};
	PPCCRRegister cr0{};
	PPCCRRegister cr6{};
	PPCRegister r15{};
	PPCRegister r16{};
	PPCRegister r17{};
	PPCRegister r18{};
	PPCRegister r19{};
	PPCRegister r20{};
	PPCRegister r21{};
	PPCRegister r22{};
	PPCRegister r23{};
	PPCRegister r24{};
	PPCRegister r25{};
	PPCRegister r26{};
	PPCRegister r27{};
	PPCRegister r28{};
	PPCRegister r29{};
	PPCRegister r30{};
	PPCRegister r31{};
	PPCRegister f31{};
	PPCRegister temp{};
	uint32_t ea{};
	ctx.r12.u64 = ctx.lr;
	ctx.lr = 0x82C65F10;
	REX_STORE_D_U64(ctx.r1.u32, -152, f31.u64);
	ea = -240 + ctx.r1.u32;
	REX_STORE_U32(ea, ctx.r1.u32);
	ctx.r1.u32 = ea;
	ctx.r11.s64 = -2112094208;
	ctx.r10.s64 = 0;
	ctx.r9.s64 = ctx.r11.s64 + -4192;
	ctx.r8.s64 = 6356992;
	ctx.r7.s64 = 0;
	ctx.r6.s64 = 6356992;
	ctx.r5.s64 = 0;
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_D_U32(ctx.r9.u32, 320);
	f31.f64 = double(temp.f32);
	r31.u64 = ctx.r3.u64;
	r25.s64 = 0;
	r27.s64 = 1;
	r15.u64 = ctx.r10.u64 | 57660;
	r16.u64 = ctx.r8.u64 | 22200;
	r28.u64 = ctx.r7.u64 | 57828;
	r18.s64 = -2096693248;
	r21.s64 = 3;
	r17.u64 = ctx.r6.u64 | 22204;
	r19.u64 = ctx.r5.u64 | 34296;
	r20.s64 = 2;
	r26.s64 = -2096758784;
loc_82C65F68:
	ctx.r11.u64 = REX_LOAD_D_U8(r31.u32, 61);
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C65F84;
	ctx.r11.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	ctx.r11.u64 = r25.u64;
	if (!cr6.eq) goto loc_82C65F88;
loc_82C65F84:
	ctx.r11.u64 = r27.u64;
loc_82C65F88:
	ctx.r11.u64 = ctx.r11.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C663F4;
	ctx.r3.u64 = REX_LOAD_D_U32(r31.u32, 64);
	ctx.r11.u64 = REX_LOAD_U8(ctx.r3.u32 + r15.u32);
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (cr6.eq) {
        if (idle_us > 0 && ++idle_polls >= 64) {
            std::this_thread::sleep_for(std::chrono::microseconds(idle_us));
            idle_polls = 0;
        }
        goto loc_82C65F68;
    }
    idle_polls = 0;
	ctx.r11.u64 = REX_LOAD_U8(r31.u32 + r16.u32);
	r24.u64 = r31.u64 + r16.u64;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (cr6.eq) goto loc_82C6600C;
	ctx.r6.s64 = 0;
	ctx.r5.s64 = 1;
	ctx.r4.s64 = 1;
	ctx.lr = 0x82C65FC4;
	sub_82C27718(ctx, base);
	ctx.r11.u64 = ctx.r3.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C6600C;
	ctx.r11.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	ctx.r8.u64 = REX_LOAD_D_U32(r31.u32, 44);
	ctx.r6.u64 = ctx.r8.u8 & 0x20 ? 0 : (r27.u32 << (ctx.r8.u8 & 0x3F));
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + r28.u32);
	ctx.r5.u64 = ~ctx.r6.u64;
	ctx.r4.s64 = ctx.r11.s64 + 4308;
loc_82C65FE8:
	// mfmsr r7
	// mtmsrd r13,1
	ea = ctx.r4.u32;
	reserved.u32 = *(uint32_t*)REX_RAW_ADDR(ea);
	ctx.r10.u64 = __builtin_bswap32(reserved.u32);
	ctx.r9.u64 = ctx.r5.u64 & ctx.r10.u64;
	// stwcx. r9,0,r4
	ea = ctx.r4.u32;
	cr0.lt = 0;
	cr0.gt = 0;
	cr0.eq = __sync_bool_compare_and_swap(reinterpret_cast<uint32_t*>(REX_RAW_ADDR(ea)), reserved.s32, __builtin_bswap32(ctx.r9.s32));
	cr0.so = xer.so;
	// mtmsrd r7,1
	if (!cr0.eq) goto loc_82C65FE8;
	REX_STORE_D_U32(r31.u32, 48, r21.u32);
	REX_STORE_D_U8(r24.u32, 0, r25.u8);
loc_82C6600C:
	ctx.r11.u64 = REX_LOAD_D_U32(r31.u32, 44);
	cr6.compare<int32_t>(ctx.r11.s32, 0, xer);
	if (!cr6.eq) goto loc_82C6603C;
	ctx.r11.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	ctx.r11.u64 = ctx.r11.u64 + r28.u64;
	ctx.r10.u64 = REX_LOAD_D_U32(ctx.r11.u32, 0);
	ctx.r9.u64 = REX_LOAD_D_U32(ctx.r10.u32, 4312);
	cr6.compare<uint32_t>(ctx.r9.u32, 0, xer);
	if (cr6.eq) goto loc_82C6603C;
	ctx.r11.u64 = REX_LOAD_D_U32(ctx.r11.u32, 0);
	ctx.r3.u64 = REX_LOAD_D_U32(ctx.r11.u32, 4312);
	ctx.lr = 0x82C6603C;
	sub_82C711D0(ctx, base);
loc_82C6603C:
	ctx.r11.u64 = REX_LOAD_D_U8(r31.u32, 52);
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (cr6.eq) goto loc_82C660F8;
	ctx.r11.u64 = REX_LOAD_D_U32(r31.u32, 48);
	cr6.compare<int32_t>(ctx.r11.s32, 3, xer);
	if (!cr6.eq) goto loc_82C66064;
	ctx.r3.u64 = r31.u64 + r17.u64;
	ctx.lr = 0x82C6605C;
	sub_82C64F38(ctx, base);
	REX_STORE_D_U8(r31.u32, 52, r25.u8);
	goto loc_82C660F4;
loc_82C66064:
	ctx.r6.s64 = 0;
	ctx.r3.u64 = REX_LOAD_D_U32(r31.u32, 64);
	ctx.r5.s64 = 1;
	ctx.r4.s64 = 0;
	ctx.lr = 0x82C66078;
	sub_82C27718(ctx, base);
	ctx.r11.u64 = ctx.r3.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C660C8;
	ctx.r11.u64 = REX_LOAD_D_U32(r31.u32, 64);
	ctx.r9.u64 = ctx.r11.u64 + r19.u64;
	ctx.r3.u64 = ctx.r9.u64;
	ctx.lr = 0x82C66094;
	sub_82C197A8(ctx, base);
	ctx.r10.u64 = ctx.r3.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r10.u32, 0, xer);
	if (!cr6.eq) goto loc_82C660B0;
	ctx.r11.u64 = REX_LOAD_D_U32(ctx.r9.u32, 280);
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	ctx.r11.u64 = r25.u64;
	if (cr6.eq) goto loc_82C660B4;
loc_82C660B0:
	ctx.r11.u64 = r27.u64;
loc_82C660B4:
	ctx.r11.u64 = ctx.r11.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C660C8;
	REX_STORE_D_U8(r31.u32, 52, r25.u8);
	goto loc_82C660F4;
loc_82C660C8:
	ctx.lr = 0x82C660CC;
	sub_82B65880(ctx, base);
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_D_U32(r31.u32, 56);
	ctx.f0.f64 = double(temp.f32);
	ctx.f13.f64 = double(float(ctx.f1.f64 - ctx.f0.f64));
	cr6.compare(ctx.f13.f64, f31.f64);
	if (!cr6.gt) goto loc_82C660F8;
	REX_STORE_D_U8(r31.u32, 52, r25.u8);
	ctx.r11.u64 = REX_LOAD_D_U32(r31.u32, 64);
	ctx.r3.u64 = ctx.r11.u64 + r19.u64;
	ctx.lr = 0x82C660EC;
	sub_82C19BC0(ctx, base);
	ctx.r3.s64 = ctx.r3.s64 + 276;
	ctx.lr = 0x82C660F4;
	sub_822C9240(ctx, base);
loc_82C660F4:
	REX_STORE_D_U32(r31.u32, 48, r27.u32);
loc_82C660F8:
	r22.u64 = r25.u64;
loc_82C660FC:
	r23.u64 = REX_LOAD_D_U32(r31.u32, 48);
	ctx.r11.u64 = REX_LOAD_D_U32(r31.u32, 48);
	ctx.r11.s64 = ctx.r11.s64 + -1;
	cr6.compare<uint32_t>(ctx.r11.u32, 9, xer);
	if (cr6.gt) goto loc_82C663D8;
	ctx.r12.s64 = -2100953088;
	ctx.r0.u64 = ((uint32_t)(ctx.r11.u32 << 2));
	ctx.r12.s64 = ctx.r12.s64 + 24872;
	ctx.r0.u64 = REX_LOAD_U32(ctx.r12.u32 + ctx.r0.u32);
	ctr.u64 = ctx.r0.u64;
	switch (ctx.r11.u32) {
	case 0:
		goto loc_82C66150;
	case 1:
		goto loc_82C661B8;
	case 2:
		goto loc_82C661AC;
	case 3:
		goto loc_82C6636C;
	case 4:
		goto loc_82C66380;
	case 5:
		goto loc_82C66394;
	case 6:
		goto loc_82C6639C;
	case 7:
		goto loc_82C663B0;
	case 8:
		goto loc_82C663C4;
	case 9:
		goto loc_82C663CC;
	default:
		__builtin_trap(); // Switch case out of range
	}
loc_82C66150:
	ctx.r11.u64 = REX_LOAD_D_U8(r31.u32, 5);
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C661AC;
	ctx.r3.u64 = REX_LOAD_D_U32(r18.u32, -17692);
	ctx.lr = 0x82C66164;
	sub_82DA3668(ctx, base);
	ctx.r11.u64 = ctx.r3.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C661AC;
	REX_STORE_D_U8(r24.u32, 0, r25.u8);
	ctx.r8.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	ctx.r6.u64 = REX_LOAD_D_U32(r31.u32, 44);
	ctx.r5.u64 = ctx.r6.u8 & 0x20 ? 0 : (r27.u32 << (ctx.r6.u8 & 0x3F));
	ctx.r11.u64 = REX_LOAD_U32(ctx.r8.u32 + r28.u32);
	ctx.r4.s64 = ctx.r11.s64 + 4308;
loc_82C66188:
	// mfmsr r7
	// mtmsrd r13,1
	ea = ctx.r4.u32;
	reserved.u32 = *(uint32_t*)REX_RAW_ADDR(ea);
	ctx.r10.u64 = __builtin_bswap32(reserved.u32);
	ctx.r9.u64 = ctx.r5.u64 | ctx.r10.u64;
	// stwcx. r9,0,r4
	ea = ctx.r4.u32;
	cr0.lt = 0;
	cr0.gt = 0;
	cr0.eq = __sync_bool_compare_and_swap(reinterpret_cast<uint32_t*>(REX_RAW_ADDR(ea)), reserved.s32, __builtin_bswap32(ctx.r9.s32));
	cr0.so = xer.so;
	// mtmsrd r7,1
	if (!cr0.eq) goto loc_82C66188;
	REX_STORE_D_U32(r31.u32, 48, r20.u32);
	goto loc_82C663D8;
loc_82C661AC:
	ctx.r3.s64 = 1;
	ctx.lr = 0x82C661B4;
	sub_823B2DB8(ctx, base);
	goto loc_82C663D8;
loc_82C661B8:
	ctx.r11.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	ctx.r7.u64 = REX_LOAD_D_U32(r31.u32, 44);
	ctx.r6.u64 = ctx.r7.u8 & 0x20 ? 0 : (r27.u32 << (ctx.r7.u8 & 0x3F));
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + r28.u32);
	ctx.r5.s64 = ctx.r11.s64 + 4308;
loc_82C661CC:
	// mfmsr r8
	// mtmsrd r13,1
	ea = ctx.r5.u32;
	reserved.u32 = *(uint32_t*)REX_RAW_ADDR(ea);
	ctx.r10.u64 = __builtin_bswap32(reserved.u32);
	ctx.r9.u64 = ctx.r6.u64 | ctx.r10.u64;
	// stwcx. r9,0,r5
	ea = ctx.r5.u32;
	cr0.lt = 0;
	cr0.gt = 0;
	cr0.eq = __sync_bool_compare_and_swap(reinterpret_cast<uint32_t*>(REX_RAW_ADDR(ea)), reserved.s32, __builtin_bswap32(ctx.r9.s32));
	cr0.so = xer.so;
	// mtmsrd r8,1
	if (!cr0.eq) goto loc_82C661CC;
	ctx.r11.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	ctx.r11.u64 = ctx.r11.u64 + r28.u64;
	ctx.r4.u64 = REX_LOAD_D_U32(ctx.r11.u32, 0);
	ctx.r3.u64 = REX_LOAD_D_U8(ctx.r4.u32, 4304);
	cr6.compare<uint32_t>(ctx.r3.u32, 0, xer);
	if (!cr6.eq) goto loc_82C66234;
	ctx.r10.u64 = REX_LOAD_D_U32(r31.u32, 44);
	ctx.r11.u64 = REX_LOAD_D_U32(ctx.r11.u32, 0);
	ctx.r6.u64 = ctx.r10.u8 & 0x20 ? 0 : (r27.u32 << (ctx.r10.u8 & 0x3F));
	ctx.r5.u64 = ~ctx.r6.u64;
	ctx.r4.s64 = ctx.r11.s64 + 4308;
loc_82C66214:
	// mfmsr r7
	// mtmsrd r13,1
	ea = ctx.r4.u32;
	reserved.u32 = *(uint32_t*)REX_RAW_ADDR(ea);
	ctx.r9.u64 = __builtin_bswap32(reserved.u32);
	ctx.r8.u64 = ctx.r5.u64 & ctx.r9.u64;
	// stwcx. r8,0,r4
	ea = ctx.r4.u32;
	cr0.lt = 0;
	cr0.gt = 0;
	cr0.eq = __sync_bool_compare_and_swap(reinterpret_cast<uint32_t*>(REX_RAW_ADDR(ea)), reserved.s32, __builtin_bswap32(ctx.r8.s32));
	cr0.so = xer.so;
	// mtmsrd r7,1
	if (!cr0.eq) goto loc_82C66214;
	goto loc_82C663D8;
loc_82C66234:
	ctx.r3.u64 = r31.u64;
	ctx.lr = 0x82C6623C;
	sub_82C65B20(ctx, base);
	ctx.r11.u64 = ctx.r3.u32 & 0xFF;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	ctx.r11.u64 = REX_LOAD_D_U32(r26.u32, 20332);
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + r28.u32);
	ctx.r4.s64 = ctx.r11.s64 + 4308;
	if (!cr6.eq) goto loc_82C66280;
	ctx.r8.u64 = REX_LOAD_D_U32(r31.u32, 44);
	ctx.r6.u64 = ctx.r8.u8 & 0x20 ? 0 : (r27.u32 << (ctx.r8.u8 & 0x3F));
	ctx.r5.u64 = ~ctx.r6.u64;
loc_82C66260:
	// mfmsr r7
	// mtmsrd r13,1
	ea = ctx.r4.u32;
	reserved.u32 = *(uint32_t*)REX_RAW_ADDR(ea);
	ctx.r10.u64 = __builtin_bswap32(reserved.u32);
	ctx.r9.u64 = ctx.r5.u64 & ctx.r10.u64;
	// stwcx. r9,0,r4
	ea = ctx.r4.u32;
	cr0.lt = 0;
	cr0.gt = 0;
	cr0.eq = __sync_bool_compare_and_swap(reinterpret_cast<uint32_t*>(REX_RAW_ADDR(ea)), reserved.s32, __builtin_bswap32(ctx.r9.s32));
	cr0.so = xer.so;
	// mtmsrd r7,1
	if (!cr0.eq) goto loc_82C66260;
	goto loc_82C663D8;
loc_82C66280:
	ctx.r7.u64 = REX_LOAD_D_U32(r31.u32, 44);
	ctx.r6.u64 = ctx.r7.u8 & 0x20 ? 0 : (r27.u32 << (ctx.r7.u8 & 0x3F));
	ctx.r5.u64 = ~ctx.r6.u64;
loc_82C6628C:
	// mfmsr r8
	// mtmsrd r13,1
	ea = ctx.r4.u32;
	reserved.u32 = *(uint32_t*)REX_RAW_ADDR(ea);
	ctx.r10.u64 = __builtin_bswap32(reserved.u32);
	ctx.r9.u64 = ctx.r5.u64 & ctx.r10.u64;
	// stwcx. r9,0,r4
	ea = ctx.r4.u32;
	cr0.lt = 0;
	cr0.gt = 0;
	cr0.eq = __sync_bool_compare_and_swap(reinterpret_cast<uint32_t*>(REX_RAW_ADDR(ea)), reserved.s32, __builtin_bswap32(ctx.r9.s32));
	cr0.so = xer.so;
	// mtmsrd r8,1
	if (!cr0.eq) goto loc_82C6628C;
	REX_STORE_D_U32(r31.u32, 48, r21.u32);
	ctx.r4.s64 = 0;
	REX_STORE_D_U8(r24.u32, 0, r25.u8);
	ctx.r3.u64 = REX_LOAD_D_U32(r31.u32, 64);
	ctx.lr = 0x82C662BC;
	sub_82C25E88(ctx, base);
	r30.u64 = ctx.r3.u64;
loc_82C662C0:
	ctx.r10.u64 = REX_LOAD_D_U32(r30.u32, 4);
	ctx.r11.u64 = REX_LOAD_D_U32(r30.u32, 8);
	cr6.compare<uint32_t>(ctx.r10.u32, 0, xer);
	if (cr6.eq) goto loc_82C662E8;
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C662E0;
	ctx.r11.u64 = REX_LOAD_D_U32(ctx.r10.u32, 44);
	goto loc_82C66304;
loc_82C662E0:
	ctx.r11.u64 = REX_LOAD_D_U32(ctx.r11.u32, 12);
	goto loc_82C66304;
loc_82C662E8:
	cr6.compare<uint32_t>(ctx.r11.u32, 0, xer);
	if (!cr6.eq) goto loc_82C66300;
	ctx.r11.u64 = REX_LOAD_D_U32(r30.u32, 0);
	ctx.r10.u64 = REX_LOAD_D_U32(ctx.r11.u32, 16);
	REX_STORE_D_U32(r30.u32, 8, ctx.r10.u32);
	goto loc_82C66308;
loc_82C66300:
	ctx.r11.u64 = REX_LOAD_D_U32(ctx.r11.u32, 8);
loc_82C66304:
	REX_STORE_D_U32(r30.u32, 8, ctx.r11.u32);
loc_82C66308:
	r29.u64 = REX_LOAD_D_U32(r30.u32, 8);
	cr6.compare<uint32_t>(r29.u32, 0, xer);
	if (cr6.eq) goto loc_82C66360;
	ctx.r11.u64 = REX_LOAD_D_U32(r29.u32, 48);
	ctx.r10.u64 = REX_LOAD_D_U32(r29.u32, 44);
	cr6.compare<int32_t>(ctx.r11.s32, ctx.r10.s32, xer);
	if (cr6.eq) goto loc_82C662C0;
	cr6.compare<int32_t>(ctx.r11.s32, 2, xer);
	if (!cr6.eq) goto loc_82C66344;
	ctx.r4.s64 = 0;
	ctx.r3.u64 = r29.u64;
	ctx.lr = 0x82C66338;
	sub_82BE9690(ctx, base);
	ctx.r11.u64 = REX_LOAD_D_U32(r29.u32, 44);
	REX_STORE_D_U32(r29.u32, 48, ctx.r11.u32);
	goto loc_82C662C0;
loc_82C66344:
	cr6.compare<int32_t>(ctx.r11.s32, 0, xer);
	if (!cr6.eq) goto loc_82C66354;
	ctx.r3.u64 = r29.u64;
	ctx.lr = 0x82C66354;
	sub_82BE64B8(ctx, base);
loc_82C66354:
	ctx.r11.u64 = REX_LOAD_D_U32(r29.u32, 44);
	REX_STORE_D_U32(r29.u32, 48, ctx.r11.u32);
	goto loc_82C662C0;
loc_82C66360:
	REX_STORE_D_U32(r30.u32, 8, r25.u32);
	REX_STORE_D_U32(r30.u32, 0, r25.u32);
	goto loc_82C663D8;
loc_82C6636C:
	ctx.r5.s64 = 0;
	ctx.r4.s64 = 0;
	ctx.r3.u64 = r31.u64;
	ctx.lr = 0x82C6637C;
	sub_82C64A50(ctx, base);
	goto loc_82C663D8;
loc_82C66380:
	ctx.r5.s64 = 2;
	ctx.r4.s64 = 0;
	ctx.r3.u64 = r31.u64;
	ctx.lr = 0x82C66390;
	sub_82C64A50(ctx, base);
	goto loc_82C663D8;
loc_82C66394:
	ctx.r4.s64 = 0;
	goto loc_82C663D0;
loc_82C6639C:
	ctx.r5.s64 = 0;
	ctx.r4.s64 = 1;
	ctx.r3.u64 = r31.u64;
	ctx.lr = 0x82C663AC;
	sub_82C64A50(ctx, base);
	goto loc_82C663D8;
loc_82C663B0:
	ctx.r5.s64 = 2;
	ctx.r4.s64 = 2;
	ctx.r3.u64 = r31.u64;
	ctx.lr = 0x82C663C0;
	sub_82C64A50(ctx, base);
	goto loc_82C663D8;
loc_82C663C4:
	ctx.r4.s64 = 1;
	goto loc_82C663D0;
loc_82C663CC:
	ctx.r4.s64 = 2;
loc_82C663D0:
	ctx.r3.u64 = r31.u64;
	ctx.lr = 0x82C663D8;
	sub_82C65C50(ctx, base);
loc_82C663D8:
	ctx.r11.u64 = REX_LOAD_D_U32(r31.u32, 48);
	cr6.compare<int32_t>(ctx.r11.s32, r23.s32, xer);
	if (cr6.eq) goto loc_82C65F68;
	cr6.compare<int32_t>(r22.s32, 5, xer);
	if (cr6.gt) goto loc_82C65F68;
	r22.s64 = r22.s64 + 1;
	goto loc_82C660FC;
loc_82C663F4:
	ctx.r1.s64 = ctx.r1.s64 + 240;
	f31.u64 = REX_LOAD_D_U64(ctx.r1.u32, -152);
	return;
}
