public class Test02 {
    public static void main(String[] args) throws Exception {
        System.out.println("🚀 Iniciando Test02");

        for (int i = 0; i < 5; i++) {
            Thread.sleep(200 + (long)(Math.random() * 300));
            if (i == 2) {
                throw new RuntimeException("Falha simulada no loop " + i);
            }
            System.out.println("✅ Iteração " + i + " concluída");
        }

        System.out.println("🏁 Finalizando Test02");
    }
}
