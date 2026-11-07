import { z } from 'zod'

export const universityEmailSchema = z
  .string()
  .trim()
  .toLowerCase()
  .min(1, 'Vui lòng nhập email')
  .max(254, 'Email quá dài')
  .email('Email không hợp lệ')
  .refine(
    (value) => value.split('@')[1] === 'university.edu.vn',
    'Vui lòng sử dụng email trường có đuôi @university.edu.vn'
  )

export const newPasswordSchema = z
  .string()
  .min(15, 'Mật khẩu phải có ít nhất 15 ký tự')
  .max(128, 'Mật khẩu tối đa 128 ký tự')

export const registrationSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, 'Vui lòng nhập họ tên')
      .max(100, 'Họ tên quá dài'),
    email: universityEmailSchema,
    password: newPasswordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Mật khẩu xác nhận không khớp',
  })
